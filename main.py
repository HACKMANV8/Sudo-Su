import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocessing.spacy_preprocessor import SpacyTextPreprocessor

def main():
    print("Starting Text Preprocessing with spaCy...")
    
    # Initialize preprocessor
    preprocessor = SpacyTextPreprocessor()
    
    try:
        # Option 1: Process CSV file
        print("\nProcessing CSV file...")
        processed_data = preprocessor.preprocess_csv(
            csv_path="data/sample.csv",
            text_column="text",
            output_path="data/processed_data.csv"
        )
        
        # Option 2: Process individual texts
        print("\n Processing individual texts...")
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
        
        print(f"\nAll preprocessing completed successfully!")
        print(f"Processed {len(processed_data)} rows from CSV")
        print(f"Processed {len(custom_texts)} custom texts")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()