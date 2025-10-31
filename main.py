import sys
import os
import argparse
import glob
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from intent.intent_parser import parse_intent
from schema.schema_builder import build_schema_for_csv, build_schema_from_intent
from metadata.augmenter import augment_metadata, augment_from_schema
from review.schema_review import review_schemas_in_dir


def main():
    """Intent-only entrypoint: interpret NL request into DatasetIntent JSON."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Interpret user intent, build schemas, and augment metadata for CSVs in data/")
    parser.add_argument("--prompt", dest="prompt", type=str, required=False,
                        help="Natural language description of the desired dataset")
    parser.add_argument("--out", dest="out", type=str, default="specs/intent.json",
                        help="Output path for the intent JSON (default: specs/intent.json)")
    parser.add_argument("--data_dir", dest="data_dir", type=str, default="data",
                        help="Directory containing CSV files (default: data)")
    parser.add_argument("--rows", dest="rows", type=int, default=20,
                        help="Number of sample rows to include in prompts (default: 20)")
    parser.add_argument("--use_csv", dest="use_csv", choices=["ask","yes","no"], default="ask",
                        help="Whether to use CSV context (ask/yes/no). Default ask")
    parser.add_argument("--hil", dest="hil", action="store_true",
                        help="Enable Human-in-the-Loop schema review at the end")
    args = parser.parse_args()

    prompt = args.prompt or os.getenv("INTENT_PROMPT")
    if not prompt:
        # Try to collect prompt interactively; fall back to example if unavailable
        try:
            user_in = input(
                "ON what topic you need the schema give the query for it: "
            ).strip()
        except Exception:
            user_in = ""
        if user_in:
            prompt = user_in
        else:
            prompt = (
                "Create a customer feedback dataset for a food delivery app, with sentiment, category, and timestamp. ~5k rows."
            )
            print("Using example prompt (no input provided).")

    try:
        intent = parse_intent(prompt, save_path=args.out)
        print("\n✅ Intent parsed and validated.")
        print(f"Saved to: {args.out}")
        os.makedirs("specs", exist_ok=True)

        # Decide CSV usage
        use_csv = None
        if args.use_csv == "yes":
            use_csv = True
        elif args.use_csv == "no":
            use_csv = False
        else:
            # ask interactively if possible
            try:
                answer = input("Use CSV files in 'data/' to ground the schema/metadata? [Y/n]: ").strip().lower()
                use_csv = (answer in ["", "y", "yes"])
            except Exception:
                use_csv = True

        generated_schema_files = []

        if use_csv:
            # Discover CSV files
            csv_files = sorted(glob.glob(os.path.join(args.data_dir, "*.csv")))
            if not csv_files:
                print(f"No CSV files found in {args.data_dir}. Skipping schema/metadata steps.")
            else:
                for csv_path in csv_files:
                    base = os.path.splitext(os.path.basename(csv_path))[0]
                    schema_out = os.path.join("specs", f"{base}_schema.json")
                    meta_out = os.path.join("specs", f"{base}_metadata.json")

                    print(f"\n🧩 Building schema for: {csv_path}")
                    schema = build_schema_for_csv(csv_path, natural_prompt=prompt, n_rows=args.rows)
                    with open(schema_out, 'w') as f:
                        json.dump(schema, f, indent=2)
                    generated_schema_files.append(schema_out)
                    print(f"   • Wrote {schema_out}")

                    print(f"📝 Augmenting metadata for: {csv_path}")
                    metadata = augment_metadata(csv_path, schema=schema, natural_prompt=prompt, n_rows=max(args.rows, 50))
                    with open(meta_out, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    print(f"   • Wrote {meta_out}")
        else:
            # Build schema purely from intent
            only_out = os.path.join("specs", "intent_only_schema.json")
            print("\n🧩 Building schema from intent only (no CSV context)...")
            schema = build_schema_from_intent(prompt)
            with open(only_out, 'w') as f:
                json.dump(schema, f, indent=2)
            generated_schema_files.append(only_out)
            print(f"   • Wrote {only_out}")

            # Augment metadata from schema + intent (no CSV profile)
            meta_out = os.path.join("specs", "intent_only_metadata.json")
            print("📝 Augmenting metadata from schema (no CSV)...")
            metadata = augment_from_schema(schema, natural_prompt=prompt)
            with open(meta_out, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"   • Wrote {meta_out}")

        # Human-in-the-loop review
        start_hil = args.hil
        if not start_hil and generated_schema_files:
            try:
                ans = input("Start schema review now? [y/N]: ").strip().lower()
                start_hil = (ans == 'y')
            except Exception:
                start_hil = False
        if start_hil and generated_schema_files:
            print("\n🧑‍⚖️ Starting schema review...")
            review_schemas_in_dir("specs")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()