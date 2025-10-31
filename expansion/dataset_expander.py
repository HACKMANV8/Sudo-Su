import pandas as pd
from typing import List, Dict, Any
import logging
from tqdm import tqdm
import os

from .paraphrase_generator import ParaphraseGenerator
from .template_engine import TemplateEngine
from .gemini_generator import GeminiGenerator

class DatasetExpander:
    def __init__(self, use_gemini: bool = True, gemini_api_key: str = None):
        self.logger = self._setup_logging()
        self.use_gemini = use_gemini
        
        if use_gemini:
            self.gemini_generator = GeminiGenerator(api_key=gemini_api_key)
            self.logger.info("✅ Using Gemini for dataset expansion")
        else:
            self.paraphraser = ParaphraseGenerator()
            self.logger.info("✅ Using T5 for dataset expansion")
            
        self.template_engine = TemplateEngine()
        self.logger.info("✅ Dataset Expander initialized")
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def expand_text(self, text: str, num_variations: int = 2) -> List[str]:
        """Expand a single text using Gemini + Templates"""
        expanded_texts = []
        
        if self.use_gemini:
            # Use Gemini for high-quality variations
            self.logger.info(f"Generating Gemini variations for: {text[:50]}...")
            gemini_variations = self.gemini_generator.generate_variations(
                text, 
                num_variations=num_variations,
                style="paraphrase"
            )
            expanded_texts.extend(gemini_variations)
        else:
            # Fallback to T5
            self.logger.info(f"Generating T5 paraphrases for: {text[:50]}...")
            paraphrases = self.paraphraser.generate_paraphrases(text, num_variations)
            expanded_texts.extend(paraphrases)
        
        # Always use template-based generation for structural diversity
        self.logger.info(f"Generating template variations...")
        templates = self.template_engine.generate_from_templates([text], num_variations)
        expanded_texts.extend(templates)
        
        # Remove duplicates and original text
        expanded_texts = list(set(expanded_texts))
        if text in expanded_texts:
            expanded_texts.remove(text)
        
        # Quality filtering
        if self.use_gemini:
            expanded_texts = self.gemini_generator.validate_and_filter(text, expanded_texts)
        
        return expanded_texts
    
    def expand_dataframe(self, df: pd.DataFrame, text_column: str = "text", 
                        expansion_factor: int = 3) -> pd.DataFrame:
        """Expand an entire DataFrame"""
        self.logger.info(f"Starting dataset expansion for {len(df)} rows...")
        
        expanded_rows = []
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Expanding dataset"):
            original_text = row[text_column]
            
            # Skip empty texts
            if not original_text or pd.isna(original_text):
                continue
                
            # Generate expanded versions
            expanded_texts = self.expand_text(original_text, expansion_factor)
            
            # Create new rows for each expanded text
            for expanded_text in expanded_texts:
                new_row = row.copy()
                new_row[text_column] = expanded_text
                new_row['expansion_type'] = 'generated'
                new_row['original_text'] = original_text
                new_row['generation_method'] = 'gemini+template' if self.use_gemini else 't5+template'
                expanded_rows.append(new_row)
            
            # Keep original row with metadata
            original_row = row.copy()
            original_row['expansion_type'] = 'original'
            original_row['original_text'] = original_text
            original_row['generation_method'] = 'original'
            expanded_rows.append(original_row)
        
        # Create expanded DataFrame
        expanded_df = pd.DataFrame(expanded_rows)
        expanded_df = expanded_df.reset_index(drop=True)
        
        self.logger.info(f"✅ Dataset expanded from {len(df)} to {len(expanded_df)} rows")
        return expanded_df
    
    def expand_csv(self, input_path: str, output_path: str, text_column: str = "text", 
                  expansion_factor: int = 3) -> pd.DataFrame:
        """Expand a CSV file and save results"""
        try:
            # Read input CSV
            df = pd.read_csv(input_path)
            self.logger.info(f"📁 Loaded {len(df)} rows from {input_path}")
            
            # Expand dataset
            expanded_df = self.expand_dataframe(df, text_column, expansion_factor)
            
            # Save results
            expanded_df.to_csv(output_path, index=False)
            self.logger.info(f"💾 Expanded dataset saved to {output_path}")
            
            # Show sample results
            self._show_expansion_samples(expanded_df, text_column)
            
            return expanded_df
            
        except Exception as e:
            self.logger.error(f"Error expanding CSV: {e}")
            raise
    
    def _show_expansion_samples(self, df: pd.DataFrame, text_column: str):
        """Show samples of expanded data"""
        print("\n" + "="*60)
        print("📊 GEMINI DATASET EXPANSION SAMPLES")
        print("="*60)
        
        # Group by original text to show expansions
        original_texts = df[df['expansion_type'] == 'original'][text_column].unique()
        
        for original in original_texts[:2]:  # Show first 2 originals
            expansions = df[(df['original_text'] == original) & 
                          (df['expansion_type'] == 'generated')][text_column].tolist()
            
            print(f"\n🎯 Original: {original}")
            print("🔄 Expansions:")
            for i, expansion in enumerate(expansions[:3], 1):
                print(f"   {i}. {expansion}")