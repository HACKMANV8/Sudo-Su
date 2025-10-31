import spacy
import pandas as pd
from spacy import displacy
from collections import Counter
import re
import logging

class AdvancedSpacyPreprocessor:
    def __init__(self, model_name="en_core_web_sm"):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            
        self.nlp = spacy.load(model_name)
        self.logger.info(" Advanced spaCy preprocessor loaded!")
    
    def analyze_text(self, text: str) -> dict:
        """Comprehensive text analysis"""
        doc = self.nlp(text)
        
        analysis = {
            "entities": [(ent.text, ent.label_) for ent in doc.ents],
            "noun_phrases": [chunk.text for chunk in doc.noun_chunks],
            "verbs": [token.lemma_ for token in doc if token.pos_ == "VERB"],
            "adjectives": [token.lemma_ for token in doc if token.pos_ == "ADJ"],
            "pos_tags": [(token.text, token.pos_, token.tag_) for token in doc],
            "dependency_tree": [(token.text, token.dep_, token.head.text) for token in doc]
        }
        
        return analysis
    
    def extract_entities(self, text: str) -> dict:
        """Extract named entities from text"""
        doc = self.nlp(text)
        
        entities = {
            "PERSON": [],
            "ORG": [],
            "GPE": [],  # Geographical locations
            "DATE": [],
            "MONEY": [],
            "PRODUCT": []
        }
        
        for ent in doc.ents:
            if ent.label_ in entities:
                entities[ent.label_].append(ent.text)
        
        return entities
    
    def get_text_stats(self, text: str) -> dict:
        """Get comprehensive text statistics"""
        doc = self.nlp(text)
        
        stats = {
            "char_count": len(text),
            "word_count": len([token for token in doc if not token.is_punct and not token.is_space]),
            "sentence_count": len(list(doc.sents)),
            "unique_words": len(set([token.lemma_ for token in doc if token.is_alpha])),
            "avg_word_length": sum([len(token) for token in doc if token.is_alpha]) / max(1, len([token for token in doc if token.is_alpha])),
            "readability_score": self._calculate_readability(text)
        }
        
        return stats
    
    def _calculate_readability(self, text: str) -> float:
        """Simple readability score (placeholder implementation)"""
        # This is a simplified version - you can implement more complex formulas
        doc = self.nlp(text)
        words = [token for token in doc if token.is_alpha]
        sentences = list(doc.sents)
        
        if len(words) == 0 or len(sentences) == 0:
            return 0
        
        avg_sentence_length = len(words) / len(sentences)
        return max(0, 100 - avg_sentence_length)

if __name__ == "__main__":
    pass