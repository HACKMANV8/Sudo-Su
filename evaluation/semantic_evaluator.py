import logging
import re
from typing import List, Tuple, Optional
import pandas as pd
from sentence_transformers import SentenceTransformer


def _normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _words(text: str) -> List[str]:
    text = re.sub(r"[^a-zA-Z\s]", " ", (text or "").lower())
    return [w for w in text.split() if w]


class SemanticEvaluator:
    """Compute semantic similarity (Sentence-Transformers) and token coverage.

    No fallback: requires sentence-transformers to be installed and model to load.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        try:
            self.model: SentenceTransformer = SentenceTransformer(model_name)
            self.logger.info(f"Loaded sentence-transformer model: {model_name}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to load sentence-transformer '{model_name}'. Ensure package is installed. Error: {e}"
            )

    def similarity(self, a: str, b: str) -> float:
        """Return embedding cosine similarity in [0,1]."""
        a = _normalize(a)
        b = _normalize(b)
        if not a or not b:
            return 0.0
        emb = self.model.encode([a, b], normalize_embeddings=True)
        sim = float((emb[0] * emb[1]).sum())  # cosine in [-1,1]
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    def token_coverage(self, base_processed: str, generated: str) -> float:
        """Percent of base tokens covered in generated (allowing light inflection)."""
        base = _words(base_processed)
        words = _words(generated)
        if not base or not words:
            return 0.0

        def match_inflect(w: str, b: str) -> bool:
            if w == b:
                return True
            for suf in ("s", "es", "ed", "ing"):
                if w == b + suf:
                    return True
            if b.endswith("y") and w == b[:-1] + "ies":
                return True
            if b.endswith("s") and w == b[:-1]:
                return True
            return False

        covered = 0
        for bt in base:
            if any(match_inflect(w, bt) for w in words):
                covered += 1
        return covered / max(1, len(base))

    def score_row(self, original_processed: str, generated_text: str) -> Tuple[float, float]:
        sim = self.similarity(original_processed, generated_text)
        cov = self.token_coverage(original_processed, generated_text)
        return sim, cov

    def score_dataframe(self, df: pd.DataFrame, text_column: str = "processed_text",
                        original_ref_column: str = "original_text",
                        threshold: float = 0.75) -> pd.DataFrame:
        rows = []
        for _, row in df.iterrows():
            gen = row[text_column]
            base = row.get(original_ref_column, row.get(text_column, ""))
            sim, cov = self.score_row(str(base), str(gen))
            length_ratio = len(str(gen)) / max(1, len(str(base)))
            passes = (sim >= threshold) and (cov >= 0.7) and (0.5 <= length_ratio <= 2.0)
            r = row.copy()
            r['similarity'] = round(sim, 4)
            r['coverage'] = round(cov, 4)
            r['length_ratio'] = round(length_ratio, 3)
            r['auto_pass'] = bool(passes)
            rows.append(r)
        return pd.DataFrame(rows)

    def score_csv(self, input_path: str, output_path: Optional[str] = None,
                  text_column: str = "processed_text",
                  original_ref_column: str = "original_text",
                  threshold: float = 0.75) -> pd.DataFrame:
        df = pd.read_csv(input_path)
        scored = self.score_dataframe(df, text_column, original_ref_column, threshold)
        if output_path:
            scored.to_csv(output_path, index=False)
            self.logger.info(f"Scored dataset saved to {output_path}")
        return scored
