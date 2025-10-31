import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
from typing import List, Dict
import logging

class ParaphraseGenerator:
    def __init__(self, model_name="t5-small"):
        self.logger = self._setup_logging()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.model, self.tokenizer = self._load_model()
        self.logger.info(f"✅ Paraphrase Generator loaded with {model_name} on {self.device}")
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def _load_model(self):
        """Load T5 model for paraphrasing"""
        try:
            tokenizer = T5Tokenizer.from_pretrained(self.model_name)
            model = T5ForConditionalGeneration.from_pretrained(self.model_name)
            model = model.to(self.device)
            return model, tokenizer
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise
    
    def generate_paraphrases(self, text: str, num_variations: int = 3) -> List[str]:
        """Generate paraphrased versions of input text"""
        try:
            paraphrases = []
            
            # Different paraphrase prompts for diversity
            prompts = [
                f"paraphrase: {text}",
                f"rephrase: {text}",
                f"rewrite: {text}"
            ]
            
            for prompt in prompts[:num_variations]:
                input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
                
                # Generate with diverse beam search
                outputs = self.model.generate(
                    input_ids,
                    max_length=256,
                    num_beams=10,
                    num_return_sequences=1,
                    early_stopping=True,
                    temperature=0.7,
                    do_sample=True
                )
                
                paraphrase = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Filter out low-quality paraphrases
                if self._is_quality_paraphrase(text, paraphrase):
                    paraphrases.append(paraphrase)
            
            return list(set(paraphrases))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error generating paraphrases: {e}")
            return []
    
    def _is_quality_paraphrase(self, original: str, paraphrase: str) -> bool:
        """Basic quality check for generated paraphrases"""
        if not paraphrase or len(paraphrase) < 5:
            return False
        
        # Check if paraphrase is too similar to original
        if paraphrase.lower() == original.lower():
            return False
            
        # Check length ratio (avoid very short/long paraphrases)
        length_ratio = len(paraphrase) / len(original)
        if length_ratio < 0.3 or length_ratio > 2.0:
            return False
            
        return True
    
    def batch_paraphrase(self, texts: List[str], num_variations: int = 2) -> Dict[str, List[str]]:
        """Generate paraphrases for multiple texts"""
        results = {}
        
        for text in texts:
            self.logger.info(f"Generating paraphrases for: {text[:50]}...")
            paraphrases = self.generate_paraphrases(text, num_variations)
            results[text] = paraphrases
        
        return results