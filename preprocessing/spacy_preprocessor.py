import spacy
import pandas as pd
import re
from typing import List, Union, Dict, Any
import logging

class SpacyTextPreprocessor:
    def __init__(self, model_name="en_core_web_sm"):
        """Initialize spaCy model and components"""
        try:
            self.nlp = spacy.load(model_name)
            self.logger = self._setup_logging()
            self.logger.info(f"spaCy preprocessor loaded with model: {model_name}")
        except Exception as e:
            self.logger.error(f"Failed to load spaCy model: {e}")
            raise
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def clean_text(self, text: str) -> str:
        """Basic text cleaning before spaCy processing"""
        if pd.isna(text):
            return ""
        
        # Convert to string and lowercase
        text = str(text).lower()
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def preprocess_text(self, text: str, return_type: str = "tokens") -> Union[List[str], str, Dict[str, Any]]:
        """
        Preprocess a single text with multiple return options
        """
        try:
            # Clean text first
            cleaned_text = self.clean_text(text)
            
            # Process with spaCy
            doc = self.nlp(cleaned_text)
            
            # Extract meaningful tokens
            tokens = []
            for token in doc:
                # Filter conditions
                if (not token.is_stop and           # Remove stopwords
                    not token.is_punct and          # Remove punctuation
                    not token.is_space and          # Remove spaces
                    len(token.lemma_.strip()) > 1 and  # Remove single characters
                    token.is_alpha):                # Keep only alphabetic
                    
                    # Use the actual word if lemma is messed up
                    lemma = token.lemma_.strip()
                    if len(lemma) <= 1:  # If lemmatization gives weird results
                        lemma = token.text.lower()
                    
                    tokens.append(lemma)
            
            # Additional cleanup: remove any remaining single characters
            tokens = [token for token in tokens if len(token) > 1]
            
            if return_type == "tokens":
                return tokens
            elif return_type == "string":
                return " ".join(tokens)
            elif return_type == "full":
                return {
                    "original": text,
                    "cleaned": cleaned_text,
                    "tokens": tokens,
                    "processed_text": " ".join(tokens),
                    "sentence_count": len(list(doc.sents)),
                    "token_count": len(tokens)
                }
            else:
                raise ValueError("return_type must be 'tokens', 'string', or 'full'")
                
        except Exception as e:
            self.logger.error(f"Error processing text: {e}")
            return [] if return_type == "tokens" else "" if return_type == "string" else {}
        
    def preprocess_dataframe(self, df: pd.DataFrame, text_column: str = "text", 
                           output_column: str = "processed_text") -> pd.DataFrame:
        """
        Preprocess an entire DataFrame column
        
        Args:
            df: Input DataFrame
            text_column: Name of column containing text
            output_column: Name for output column
        """
        try:
            self.logger.info(f"Processing DataFrame with {len(df)} rows")
            
            # Create copy to avoid modifying original
            result_df = df.copy()
            
            # Process each row
            result_df[output_column] = result_df[text_column].apply(
                lambda x: self.preprocess_text(x, return_type="string")
            )
            
            # Also create tokenized version
            result_df[f"{output_column}_tokens"] = result_df[text_column].apply(
                lambda x: self.preprocess_text(x, return_type="tokens")
            )
            
            self.logger.info("DataFrame processing completed successfully")
            return result_df
            
        except Exception as e:
            self.logger.error(f"Error processing DataFrame: {e}")
            raise
    
    def preprocess_csv(self, csv_path: str, text_column: str = "text", 
                      output_path: str = None) -> pd.DataFrame:
        """
        Process a CSV file and optionally save results
        """
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            self.logger.info(f"Loaded CSV with {len(df)} rows from {csv_path}")
            
            # Process data
            processed_df = self.preprocess_dataframe(df, text_column)
            
            # Show sample results
            self._display_sample_results(processed_df, text_column)
            
            # Save if output path provided
            if output_path:
                processed_df.to_csv(output_path, index=False)
                self.logger.info(f"Processed data saved to: {output_path}")
            
            return processed_df
            
        except Exception as e:
            self.logger.error(f"Error processing CSV: {e}")
            raise
    
    def _display_sample_results(self, df: pd.DataFrame, text_column: str):
        """Display sample processing results"""
        print("\n" + "="*60)
        print("PREPROCESSING RESULTS SAMPLE")
        print("="*60)
        
        for i, row in df.head(3).iterrows():
            print(f"\nSample {i+1}:")
            print(f"Original: {row[text_column]}")
            print(f"Processed: {row['processed_text']}")
            print(f"Tokens: {row['processed_text_tokens']}")
    
    def batch_process_texts(self, texts: List[str], return_type: str = "tokens") -> List:
        """Process a list of texts"""
        try:
            self.logger.info(f"Processing batch of {len(texts)} texts")
            
            results = [self.preprocess_text(text, return_type) for text in texts]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            raise

if __name__ == "__main__":
    pass