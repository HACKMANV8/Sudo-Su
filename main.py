import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

from preprocessing.spacy_preprocessor import SpacyTextPreprocessor
from expansion.dataset_expander import DatasetExpander

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
        # STEP 3: RESULTS SUMMARY
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
        else:
            print(f"   • T5 expanded data: data/expanded_dataset_t5.csv")
        
        print(f"\n🔮 NEXT STEPS:")
        print(f"   • Module 3: Semantic Evaluation & Similarity Check")
        print(f"   • Module 4: Human-in-the-Loop Correction")
        
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