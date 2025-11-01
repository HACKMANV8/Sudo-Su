from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Callable, Union, List

import pandas as pd

from .schema_model import validate_schema, schema_summary
from .generator import generate_from_schema
from .validator import validate_dataframe, score_realism
from .artifacts import create_all_artifacts
from .explain_fast import explain_label_simple
from .utils import to_normalized_seed, short_seed_token
from .connectors.crawl4ai_adapter import Crawl4AIClient, OfflineError
from .metrics.realism import evaluate_realism
from .privacy.simulation import simulate_privacy_risk, plot_privacy_tradeoff
from .benchmark.ml_benchmark import evaluate_ml_utility
from .optimizer.smartsampler import smart_adapt
from .optimizer.adaptive_engine import run_adaptive_tuning
from .learners.relational_learner import RelationalLearner
from .generator.relational_generator import generate_relational
from .llm.prior_extractor import extract_priors_from_description, PriorsParseError
from .llm.prior_converter import convert_llm_priors_to_relational
import time

log = logging.getLogger(__name__)


def _json_canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _hash_str(s: str, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(s.encode("utf-8"))
    return h.hexdigest()
def enrich_schema_with_crawl4ai(
    schema: Dict[str, Any],
    query_hints: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 10,
    cache_ok: bool = True,
    cache_ttl: int = 7 * 24 * 3600,
    mode: str = "cache",
    bypass_cache: bool = False,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Attempt to enrich schema with Crawl4AI priors.

    Returns: (new_schema, crawl_report)
    """
    start = time.time()
    new_schema = json.loads(json.dumps(schema))
    crawl_report: Dict[str, Any] = {"used": False, "status": "skipped"}
    api_key = os.environ.get("CRAWL4AI_API_KEY")
    client = Crawl4AIClient(api_key=api_key, cache_dir=os.environ.get("CRAWL4AI_CACHE_DIR", "/tmp/openschema_crawl_cache"))
    fields = new_schema.get("fields", [])
    pages_fetched = 0
    cache_key = None
    try:
        # Basic timeout guard
        if time.time() - start > timeout_seconds:
            crawl_report.update({"used": False, "status": "timeout"})
            return new_schema, crawl_report

        for f in fields:
            name = f.get("name")
            ftype = f.get("type")
            hint = (query_hints or {}).get(name) or name
            key = _hash_str(json.dumps({"q": hint, "mode": mode}, sort_keys=True))
            cache_key = key
            try:
                pages = client.search_and_scrape(hint, max_pages=3, cache_ttl_sec=cache_ttl, bypass_cache=bypass_cache, mode=mode)
                pages_fetched += len(pages)
            except OfflineError:
                crawl_report.update({"used": False, "status": "offline", "cache_key": cache_key})
                return new_schema, crawl_report
            if time.time() - start > timeout_seconds:
                crawl_report.update({"used": False, "status": "timeout", "pages_fetched": pages_fetched, "cache_key": cache_key})
                return new_schema, crawl_report

            if ftype == "category":
                pri = client.infer_category_frequencies(pages, hint, f.get("categories"))
                if pri and pri.get("categories") and pri.get("probs") and int(pri.get("samples", 0)) >= 5:
                    f["categories"] = pri["categories"]
                    f["probs"] = pri["probs"]
            elif ftype in {"int", "float"}:
                pri = client.infer_numeric_distribution(pages, hint)
                if pri and int(pri.get("samples", 0)) >= 5:
                    # Respect existing bounds
                    fmin = f.get("min")
                    fmax = f.get("max")
                    if "mean" in pri:
                        f["mean"] = pri["mean"]
                    if "std" in pri:
                        f["std"] = max(1e-9, pri["std"])
                    if "min" in pri and (fmin is None or pri["min"] > fmin):
                        f["min"] = pri["min"]
                    if "max" in pri and (fmax is None or pri["max"] < fmax):
                        f["max"] = pri["max"]
            elif ftype == "string":
                ex = client.extract_field_examples(pages, hint, max_examples=30)
                if ex:
                    meta = new_schema.setdefault("metadata", {})
                    crawl_ex = meta.setdefault("crawl_examples", {})
                    crawl_ex[name] = ex

        crawl_report.update({
            "used": True,
            "status": "ok",
            "pages_fetched": pages_fetched,
            "cache_key": cache_key,
            "mode": mode,
            "privacy_notice": "Examples redacted for PII. Crawl used public pages and heuristics; verify before production.",
        })
        return new_schema, crawl_report
    except Exception as e:
        log = logging.getLogger(__name__)
        log.warning("Crawl4AI enrichment failed: %s", e)
        crawl_report.update({"used": False, "status": "insufficient", "error": str(e), "cache_key": cache_key})
        return new_schema, crawl_report


def _hash_file(path: str, algo: str = "md5") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline_from_schema(
    schema: Dict[str, Any],
    seed: int | str = 42,
    confirm_schema: bool = False,
    out_csv: Optional[str] = None,
    verbose: bool = False,
    source_csv: Optional[str] = None,
    mode: Optional[str] = None,
    target_rows: Optional[int] = None,
    additional_rows: Optional[int] = None,
    force: bool = False,
    progressive: bool = False,
    progress_step: int = 1000,
    generator_mode: str = "fast",
    use_rank_copula: bool = False,
    repair_policy: str = "append_index",
    anomaly_spec: Optional[Dict[str, Any]] = None,
    use_crawl4ai: bool = False,
    crawl_timeout: int = 10,
    crawl_mode: str = "cache",
    crawl_bypass_cache: bool = False,
    evaluate_realism: bool = False,
    reference_csv: Optional[str] = None,
    simulate_privacy: bool = False,
    privacy_reference_csv: Optional[str] = None,
    quasi_identifiers: Optional[List[str]] = None,
    privacy_noise_level: float = 0.01,
    privacy_sample_size: Optional[int] = None,
    ml_benchmark: bool = False,
    ml_target_column: Optional[str] = None,
    auto_adapt: bool = False,
    adapt_iterations: int = 5,
    adapt_budget: int = 1000,
    adaptive_tune: bool = False,
    tune_iterations: int = 5,
    tune_budget: int = 5000,
    objective: str = "balanced",
    learn_relations: bool = False,
    use_relational_generation: bool = False,
    rel_min_samples: int = 20,
    rel_smoothing_alpha: float = 1.0,
    use_llm_priors: bool = False,
    llm_model: str = "gemini",
    llm_temperature: float = 0.0,
    llm_cache_dir: Optional[str] = None,
    llm_bypass_cache: bool = False,
    llm_max_tokens: int = 4096,
) -> Dict[str, Any]:
    try:
        normalized = validate_schema(dict(schema))
        if confirm_schema:
            return {
                "ok": True,
                "schema": normalized,
                "schema_summary": schema_summary(normalized),
            }

        # Optional Crawl4AI enrichment
        crawl_meta = {"used": False}
        if use_crawl4ai or (normalized.get("metadata", {}).get("use_crawl4ai") is True):
            enriched, cmeta = enrich_schema_with_crawl4ai(
                normalized,
                timeout_seconds=crawl_timeout,
                mode=crawl_mode,
                bypass_cache=crawl_bypass_cache,
            )
            normalized = enriched
            crawl_meta = cmeta

        # LLM Priors Extraction
        llm_meta: Dict[str, Any] = {"used": False}
        llm_priors: Optional[Dict[str, Any]] = None
        if use_llm_priors:
            try:
                schema_fp = _hash_str(_json_canonical(normalized), algo="sha256")
                result = extract_priors_from_description(
                    schema=normalized,
                    user_description="",
                    sample_csv_path=reference_csv,
                    model=llm_model,
                    temperature=llm_temperature,
                    max_tokens=llm_max_tokens,
                    cache_dir=llm_cache_dir,
                    bypass_cache=llm_bypass_cache,
                    schema_fingerprint=schema_fp,
                    api_key_env="GEMINI_API_KEY" if llm_model == "gemini" else "OPENAI_API_KEY",
                )
                llm_priors = result.get("priors_json")
                llm_meta = {
                    "used": True,
                    "model": result.get("llm_meta", {}).get("model", llm_model),
                    "priors_cache_key": result.get("cache_key", ""),
                    "prompt_hash": result.get("llm_meta", {}).get("prompt_hash", ""),
                    "redactions": result.get("redactions", {}),
                    "execution_time_seconds": result.get("execution_time_seconds", 0),
                    "warnings": [],
                }
                
                # Merge priors into schema metadata
                if llm_priors:
                    if "metadata" not in normalized:
                        normalized["metadata"] = {}
                    normalized["metadata"]["llm_priors"] = llm_priors
                
            except PriorsParseError as e:
                log.warning("LLM priors parsing failed: %s", e)
                llm_meta["used"] = False
                llm_meta["error"] = str(e)
                llm_meta["warnings"] = [f"Priors parsing failed: {e}"]
            except Exception as e:
                log.warning("LLM priors extraction failed: %s", e)
                llm_meta["used"] = False
                llm_meta["error"] = str(e)
                llm_meta["warnings"] = [f"LLM extraction failed: {e}"]

        # Relational learning
        learned_priors: Optional[Dict[str, Any]] = None
        relational_meta: Dict[str, Any] = {"used": False}
        if learn_relations and reference_csv:
            try:
                learner = RelationalLearner(min_samples=rel_min_samples, smoothing_alpha=rel_smoothing_alpha)
                # Compute schema fingerprint for cache key
                schema_fp = _hash_str(_json_canonical(normalized), algo="sha256")
                learned_priors = learner.fit(reference_csv, normalized, schema_fp, seed=to_normalized_seed(seed))
                relational_meta["learned"] = True
                relational_meta["cache_key"] = learned_priors.get("metadata", {}).get("cache_key", "")
                relational_meta["warnings"] = learned_priors.get("warnings", [])
            except Exception as e:
                logging.getLogger(__name__).warning("Relational learning failed: %s", e)
                relational_meta["learned"] = False
                relational_meta["error"] = str(e)

        # Progressive setup (pre-fingerprint for temp progress dir)
        progress_collector: Dict[str, Any] = {"files": [], "rows": 0}
        def _on_chunk(ch_df, meta):
            import os
            base_hash = _hash_str(_json_canonical({
                "schema": normalized,
                "seed": to_normalized_seed(seed),
            }))
            safe_fp = f"sha256_{base_hash}"
            base_dir = f"/tmp/openschema_artifacts/{safe_fp}"
            os.makedirs(base_dir, exist_ok=True)
            idx = len(progress_collector["files"]) + 1
            path = os.path.join(base_dir, f"progress_{idx:04d}.csv")
            ch_df.to_csv(path, index=False)
            progress_collector["files"].append(path)
            progress_collector["rows"] += int(meta.get("rows", len(ch_df)))

        # Generation: use relational generator if enabled and priors available
        # Prefer LLM priors if available, convert to relational format
        if use_relational_generation and (llm_priors or learned_priors):
            priors_to_use = None
            if llm_priors:
                # Convert LLM priors to relational format
                try:
                    priors_to_use = convert_llm_priors_to_relational(llm_priors, normalized)
                    log.info("Converted LLM priors to relational format")
                except Exception as e:
                    log.warning("Failed to convert LLM priors to relational format: %s, trying learned_priors", e)
                    priors_to_use = learned_priors
            elif learned_priors:
                priors_to_use = learned_priors
            
            if priors_to_use:
                try:
                    n_rows_final = target_rows or normalized.get("n_rows", 1000)
                    df, rel_gen_report = generate_relational(normalized, n_rows_final, seed, priors_to_use)
                    gen_report = {"rows_generated": n_rows_final}
                    gen_report["relational"] = rel_gen_report
                    relational_meta["generation"] = True
                except Exception as e:
                    logging.getLogger(__name__).warning("Relational generation failed, falling back to standard: %s", e)
                    relational_meta["generation"] = False
                    relational_meta["fallback_error"] = str(e)
                    # Fallback to standard generation
                    df, gen_report = generate_from_schema(
                        normalized,
                        seed=seed,
                        source_csv=source_csv,
                        mode=mode,
                        target_rows=target_rows,
                        additional_rows=additional_rows,
                        force=force,
                        preview_rows=None,
                        chunk_size=progress_step if progressive else None,
                        on_chunk_generated=_on_chunk if progressive else None,
                        gen_mode=generator_mode,
                        use_rank_copula=use_rank_copula,
                        repair_policy=repair_policy,
                        anomaly_spec=anomaly_spec,
                    )
            else:
                # No priors available, fallback
                df, gen_report = generate_from_schema(
                    normalized,
                    seed=seed,
                    source_csv=source_csv,
                    mode=mode,
                    target_rows=target_rows,
                    additional_rows=additional_rows,
                    force=force,
                    preview_rows=None,
                    chunk_size=progress_step if progressive else None,
                    on_chunk_generated=_on_chunk if progressive else None,
                    gen_mode=generator_mode,
                    use_rank_copula=use_rank_copula,
                    repair_policy=repair_policy,
                    anomaly_spec=anomaly_spec,
                )
        else:
            # Standard generation
            df, gen_report = generate_from_schema(
                normalized,
                seed=seed,
                source_csv=source_csv,
                mode=mode,
                target_rows=target_rows,
                additional_rows=additional_rows,
                force=force,
                preview_rows=None,
                chunk_size=progress_step if progressive else None,
                on_chunk_generated=_on_chunk if progressive else None,
                gen_mode=generator_mode,
                use_rank_copula=use_rank_copula,
                repair_policy=repair_policy,
                anomaly_spec=anomaly_spec,
            )
        validation = validate_dataframe(df, normalized, tolerance={"class_balance": 0.01})
        realism = score_realism(df, normalized)

        csv_path = None
        csv_hash = None
        if out_csv:
            # atomic write
            dname = os.path.dirname(out_csv) or "."
            os.makedirs(dname, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", delete=False, dir=dname, encoding="utf-8", newline="") as tmp:
                df.to_csv(tmp, index=False)
                tmp_path = tmp.name
            os.replace(tmp_path, out_csv)
            csv_path = out_csv
            csv_hash = _hash_file(csv_path, algo="md5")

        # Fingerprint combines normalized schema + generation report + optional CSV hash
        fp_payload = {
            "schema": normalized,
            "generation_report": gen_report,
            "csv_hash": csv_hash,
        }
        # Include crawl cache key in fingerprint when used
        if crawl_meta.get("used") and crawl_meta.get("cache_key"):
            fp_payload["crawl_cache_key"] = crawl_meta["cache_key"]
        # Include LLM priors cache key in fingerprint
        if llm_meta.get("used") and llm_meta.get("priors_cache_key"):
            fp_payload["llm_priors_cache_key"] = llm_meta["priors_cache_key"]
        fp_hex = _hash_str(_json_canonical(fp_payload), algo="sha256")
        fingerprint = f"sha256:{fp_hex}"

        # Artifacts
        safe_fp = fingerprint.replace(":", "_")
        art_dir = f"/tmp/openschema_artifacts/{safe_fp}/images"
        artifacts = create_all_artifacts(df, normalized, art_dir)

        # Explainability (simple)
        label_field = next((f["name"] for f in normalized.get("fields", []) if f.get("type") == "bool" and f["name"] in df.columns), None)
        if label_field and isinstance(label_field, str):
            try:
                gen_report["explainability"] = explain_label_simple(df, label_field, normalized)
            except Exception as e:
                logging.getLogger(__name__).warning("Explainability failed: %s", e)

        # Optional realism evaluation against reference CSV
        if evaluate_realism and reference_csv:
            try:
                ref_df = pd.read_csv(reference_csv)
                # Derive columns
                num_cols = [f["name"] for f in normalized.get("fields", []) if f.get("type") in {"int", "float"} and f["name"] in df.columns and f["name"] in ref_df.columns]
                cat_cols = [f["name"] for f in normalized.get("fields", []) if f.get("type") == "category" and f["name"] in df.columns and f["name"] in ref_df.columns]
                realism_metrics = evaluate_realism(df, ref_df, normalized, num_cols, cat_cols)
                gen_report["realism"] = realism_metrics
            except Exception as e:
                logging.getLogger(__name__).warning("Realism evaluation failed: %s", e)

        # Seed token
        gen_report["short_seed_token"] = short_seed_token(to_normalized_seed(seed))
        if progressive:
            gen_report["progress_files"] = progress_collector["files"]
            gen_report["rows_completed"] = progress_collector["rows"]

        gen_report["crawl4ai"] = crawl_meta
        gen_report["relational"] = relational_meta
        # Privacy simulation
        if simulate_privacy and privacy_reference_csv:
            try:
                ref_df = pd.read_csv(privacy_reference_csv)
                qis = quasi_identifiers or [f["name"] for f in normalized.get("fields", []) if f.get("type") in {"int", "float", "category"}]
                pr = simulate_privacy_risk(df, ref_df, qis, attacker_sample_size=min(privacy_sample_size or 1000, len(ref_df)), noise_level=privacy_noise_level)
                gen_report["privacy_simulation"] = pr
                out_img = f"/tmp/openschema_artifacts/{safe_fp}/images/privacy_tradeoff.png"
                plot_privacy_tradeoff(df, ref_df, qis, [0.0, privacy_noise_level, privacy_noise_level * 2], out_img)
            except Exception as e:
                logging.getLogger(__name__).warning("Privacy simulation failed: %s", e)

        # ML benchmarking
        if ml_benchmark and ml_target_column and reference_csv:
            try:
                ref_df = pd.read_csv(reference_csv)
                bench = evaluate_ml_utility(df, ref_df, ml_target_column)
                gen_report["ml_benchmark"] = bench
            except Exception as e:
                logging.getLogger(__name__).warning("ML benchmark failed: %s", e)

        # Auto-adaptation loop (SmartSampler)
        if auto_adapt and ml_target_column and reference_csv:
            try:
                ref_df = pd.read_csv(reference_csv)
                def _gen_fn(sch: Dict[str, Any], n: int) -> pd.DataFrame:
                    dfx, _ = generate_from_schema(sch, seed=seed, target_rows=n, force=True)
                    return dfx
                adapt = smart_adapt(normalized, ref_df, _gen_fn, ml_target_column, iterations=adapt_iterations, budget=adapt_budget)
                gen_report["auto_adapt"] = adapt
            except Exception as e:
                logging.getLogger(__name__).warning("Auto-adapt failed: %s", e)
        # Adaptive tuning across realism/utility/privacy
        if adaptive_tune and reference_csv:
            try:
                ref_df = pd.read_csv(reference_csv)
                def _gen_fn(sch: Dict[str, Any], n: int):
                    return generate_from_schema(sch, seed=seed, target_rows=n, force=True)
                qis = [f["name"] for f in normalized.get("fields", []) if f.get("type") in {"int", "float", "category"}]
                tune_res = run_adaptive_tuning(
                    normalized,
                    ref_df,
                    _gen_fn,
                    objective=objective,
                    iterations=tune_iterations,
                    budget=tune_budget,
                    seed=to_normalized_seed(seed),
                    ml_target_column=ml_target_column,
                    quasi_identifiers=qis,
                )
                gen_report["adaptive_tuning"] = {k: v for k, v in tune_res.items() if k != "final_generation_report"}
            except Exception as e:
                logging.getLogger(__name__).warning("Adaptive tuning failed: %s", e)
        return {
            "ok": True,
            "schema": normalized,
            "generation_report": gen_report,
            "validation": validation,
            "realism": realism,
            "csv_path": csv_path,
            "fingerprint": fingerprint,
            "artifacts": artifacts,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reproduce(schema: Dict[str, Any], seed: int | str, csv_path: str) -> Dict[str, Any]:
    try:
        normalized = validate_schema(dict(schema))
        df_expected = pd.read_csv(csv_path)
        df_actual, _ = generate_from_schema(normalized, seed=seed)

        equal = df_expected.equals(df_actual)
        result: Dict[str, Any] = {"ok": equal}
        if not equal:
            # Simple diff summary: show first differing row index and column
            diff_rows = []
            for i, (row_e, row_a) in enumerate(zip(df_expected.itertuples(index=False), df_actual.itertuples(index=False))):
                if row_e != row_a:
                    diff_rows.append(i)
                    break
            result["diff"] = {
                "first_mismatch_row": diff_rows[0] if diff_rows else None,
                "shape_expected": list(df_expected.shape),
                "shape_actual": list(df_actual.shape),
            }
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def preview_then_enqueue(schema: Dict[str, Any], seed: Union[int, str], target_rows: int, job_enqueue_callback: Callable[[Callable[[], Dict[str, Any]]], Any]) -> Dict[str, Any]:
    """Generate a fast 10-row preview and enqueue a full job via callback.

    job_enqueue_callback receives a callable which, when executed, runs the full pipeline.
    """
    normalized = validate_schema(dict(schema))
    # Preview with 10 rows
    df_preview, rep_prev = generate_from_schema(
        normalized,
        seed=seed,
        preview_rows=10,
        gen_mode="fast",
    )

    # Prepare full job callable
    def full_job():
        return run_pipeline_from_schema(normalized, seed=seed, target_rows=target_rows, force=False, progressive=True)

    job = job_enqueue_callback(full_job)
    return {"preview": df_preview, "job": job}


