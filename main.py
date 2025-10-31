import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

from preprocessing.spacy_preprocessor import SpacyTextPreprocessor
from expansion.dataset_expander import DatasetExpander
from evaluation.semantic_evaluator import SemanticEvaluator
from review.human_review import review_csv

def main():
    print("🚀 Starting Hackathon Pipeline with Google Gemini")
    
    try:
        # Load environment variables from .env (so you don't have to paste the key each run)
        load_dotenv()
        # ==================================================
        # STEP 1: TEXT PREPROCESSING
        # ==================================================
        print("\n" + "="*60)
        print("STEP 1: TEXT PREPROCESSING & CLEANING")
        print("="*60)
        
        preprocessor = SpacyTextPreprocessor()
        
        # Process CSV file
        print("\n📁 Processing CSV file...")
        processed_data = preprocessor.preprocess_csv(
            csv_path="data/sample.csv",
            text_column="text",
            output_path="data/processed_data.csv"
        )
        
        # Process individual texts
        print("\n🔤 Processing individual texts...")
        custom_texts = [
            "I'm working on a hackathon project for dataset generation!",
            "Natural Language Processing is fascinating with spaCy.",
            "Can't wait to see the results after preprocessing!",
            "Email me at hello@example.com or visit http://example.org"
        ]
        
        results = preprocessor.batch_process_texts(custom_texts, return_type="full")
        
        print("\n" + "="*50)
        print("CUSTOM TEXTS PROCESSING")
        print("="*50)
        
        for i, (original, result) in enumerate(zip(custom_texts, results)):
            print(f"\nText {i+1}:")
            print(f"Original: {original}")
            print(f"Processed: {result['processed_text']}")
            print(f"Token Count: {result['token_count']}")
        
        # ==================================================
        # STEP 2: GEMINI DATASET EXPANSION
        # ==================================================
        print("\n" + "="*60)
        print("STEP 2: GEMINI DATASET EXPANSION")
        print("="*60)
        
        # Get API key from environment or user input
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("🔑 Please set your Google API key as environment variable GOOGLE_API_KEY")
            print("   Or enter it here (will not be saved):")
            api_key = input("Google API Key: ").strip()
        
        if api_key:
            expander = DatasetExpander(use_gemini=True, gemini_api_key=api_key)
            
            print("\n📈 Expanding dataset with Gemini...")
            expanded_data = expander.expand_csv(
                input_path="data/processed_data.csv",
                output_path="data/expanded_dataset_gemini.csv",
                text_column="processed_text",
                expansion_factor=2
            )

            # ==================================================
            # STEP 3: SEMANTIC EVALUATION & SIMILARITY CHECK
            # ==================================================
            print("\n" + "="*60)
            print("MODULE 3: SEMANTIC EVALUATION & SIMILARITY CHECK")
            print("="*60)
            evaluator = SemanticEvaluator()
            scored = evaluator.score_csv(
                input_path="data/expanded_dataset_gemini.csv",
                output_path="data/expanded_scored.csv",
                text_column="processed_text",
                original_ref_column="original_text",
                threshold=0.75
            )
            auto_pass_count = int(scored['auto_pass'].sum()) if 'auto_pass' in scored.columns else 0
            print(f"Auto-approved items: {auto_pass_count}/{len(scored)}")

            # ==================================================
            # STEP 4: HUMAN-IN-THE-LOOP REVIEW (optional)
            # ==================================================
            print("\n" + "="*60)
            print("MODULE 4: HUMAN-IN-THE-LOOP REVIEW (optional)")
            print("="*60)
            start_review = os.getenv('HIL_REVIEW', '').lower() in ['1','true','yes','y']
            if not start_review:
                try:
                    answer = input("Start interactive review for low-similarity items now? [y/N]: ").strip().lower()
                    start_review = answer == 'y'
                except Exception:
                    start_review = False
            if start_review:
                review_csv(
                    input_csv="data/expanded_scored.csv",
                    output_csv="data/reviewed_dataset.csv",
                    text_column="processed_text",
                    original_ref_column="original_text",
                    auto_accept_threshold=0.85,
                    only_review_below=0.85
                )
            else:
                print("Skipping interactive review. You can run it later:")
                print("- Set HIL_REVIEW=1 and re-run main.py, or")
                print("- From Python: from review.human_review import review_csv; review_csv('data/expanded_scored.csv','data/reviewed_dataset.csv')")
        else:
            print("❌ No API key provided. Using T5 fallback...")
            expander = DatasetExpander(use_gemini=False)
            expanded_data = expander.expand_csv(
                input_path="data/processed_data.csv",
                output_path="data/expanded_dataset_t5.csv",
                text_column="processed_text",
                expansion_factor=2
            )
        
        # ==================================================
        # STEP 5: RESULTS SUMMARY
        # ==================================================
        print("\n" + "="*60)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        original_size = len(processed_data) if hasattr(processed_data, '__len__') else 0
        expanded_size = len(expanded_data) if hasattr(expanded_data, '__len__') else 0
        
        print(f"\n📊 PREPROCESSING RESULTS:")
        print(f"   • Processed {original_size} rows from CSV")
        print(f"   • Processed {len(custom_texts)} custom texts")
        
        print(f"\n📈 EXPANSION RESULTS:")
        print(f"   • Original dataset: {original_size} rows")
        print(f"   • Expanded dataset: {expanded_size} rows")
        if original_size > 0:
            print(f"   • Expansion factor: {expanded_size/original_size:.1f}x")
        
        print(f"\n💾 OUTPUT FILES:")
        print(f"   • Cleaned data: data/processed_data.csv")
        if api_key:
            print(f"   • Gemini expanded data: data/expanded_dataset_gemini.csv")
            print(f"   • Scored data: data/expanded_scored.csv")
            # If review file exists, list it too
            if os.path.exists("data/reviewed_dataset.csv"):
                print(f"   • Reviewed: data/reviewed_dataset.csv")
        else:
            print(f"   • T5 expanded data: data/expanded_dataset_t5.csv")

        # ==========================
        # MODULE RESULTS SUMMARIES
        # ==========================
        if api_key:
            # Evaluation summary
            print("\n🧮 EVALUATION SUMMARY:")
            try:
                import pandas as pd
                scored_df = pd.read_csv("data/expanded_scored.csv")
                avg_sim = scored_df["similarity"].mean() if "similarity" in scored_df else None
                avg_cov = scored_df["coverage"].mean() if "coverage" in scored_df else None
                auto_pass = int(scored_df["auto_pass"].sum()) if "auto_pass" in scored_df else 0
                total = len(scored_df)
                if avg_sim is not None:
                    print(f"   • Avg similarity: {avg_sim:.3f}")
                if avg_cov is not None:
                    print(f"   • Avg coverage: {avg_cov:.3f}")
                print(f"   • Auto-approved: {auto_pass}/{total}")
            except Exception:
                print("   • Scored file not available for summary.")

            # Human review summary (if present)
            if os.path.exists("data/reviewed_dataset.csv"):
                print("\n🧑‍⚖️ HUMAN REVIEW SUMMARY:")
                try:
                    reviewed_df = pd.read_csv("data/reviewed_dataset.csv")
                    for status in ["accepted", "edited", "rejected", "pending"]:
                        count = int((reviewed_df.get("status") == status).sum()) if "status" in reviewed_df else 0
                        print(f"   • {status.capitalize()}: {count}")
                except Exception:
                    print("   • Could not read reviewed dataset summary.")
        
    except Exception as e:
        print(f"❌ Error in pipeline execution: {e}")
        import traceback
        traceback.print_exc()

def test_gemini_directly():
    """Test Gemini API directly"""
    try:
        from expansion.gemini_generator import GeminiGenerator
        
        print("🧪 Testing Gemini Directly...")
        
        # You'll need to set your API key here
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("Please set GOOGLE_API_KEY environment variable")
            return
        
        gemini = GeminiGenerator(api_key=api_key)
        
        test_texts = [
            "Machine learning is amazing",
            "Natural language processing helps computers understand human language"
        ]
        
        for text in test_texts:
            print(f"\nOriginal: {text}")
            variations = gemini.generate_variations(text, num_variations=2)
            print("Gemini Variations:")
            for i, var in enumerate(variations, 1):
                print(f"  {i}. {var}")
                
    except Exception as e:
        print(f"Gemini test failed: {e}")

if __name__ == "__main__":
    # Run complete pipeline
    main()
    
    # Uncomment to test Gemini directly
    # test_gemini_directly()