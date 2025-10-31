import random
import re
from typing import List, Dict, Tuple
import logging
from collections import defaultdict

class TemplateEngine:
    def __init__(self):
        self.logger = self._setup_logging()
        self.slot_patterns = self._initialize_patterns()
        self.vocabulary = defaultdict(list)
        self.logger.info("✅ Template Engine initialized")
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def _initialize_patterns(self) -> Dict[str, str]:
        """Initialize common sentence patterns"""
        return {
            'verb_noun': "[VERB] [NOUN]",
            'adj_noun_verb': "[ADJ] [NOUN] [VERB]",
            'noun_verb_noun': "[NOUN] [VERB] [NOUN]",
            'verb_adj_noun': "[VERB] [ADJ] [NOUN]"
        }
    
    def extract_patterns(self, sentences: List[str]) -> List[str]:
        """Extract sentence patterns from input sentences"""
        patterns = []
        
        for sentence in sentences:
            # Simple pattern extraction (you can enhance this)
            words = sentence.lower().split()
            pos_tags = self._estimate_pos_tags(words)
            
            pattern = []
            for word, pos in zip(words, pos_tags):
                if pos in ['VERB', 'NOUN', 'ADJ']:
                    pattern.append(f"[{pos}]")
                else:
                    pattern.append(word)
            
            patterns.append(" ".join(pattern))
        
        return list(set(patterns))
    
    def _estimate_pos_tags(self, words: List[str]) -> List[str]:
        """Simple POS tagging estimation (replace with spaCy for better accuracy)"""
        pos_tags = []
        
        # Common verb endings
        verb_endings = ['ing', 'ed', 'es', 's']
        # Common adjective endings  
        adj_endings = ['able', 'ible', 'al', 'ful', 'ic', 'ical', 'ish', 'ive', 'less', 'y']
        
        for word in words:
            if any(word.endswith(ending) for ending in verb_endings) and len(word) > 3:
                pos_tags.append('VERB')
            elif any(word.endswith(ending) for ending in adj_endings) and len(word) > 3:
                pos_tags.append('ADJ')
            elif len(word) > 3 and word not in ['the', 'and', 'for', 'with', 'this']:
                pos_tags.append('NOUN')
            else:
                pos_tags.append('OTHER')
        
        return pos_tags
    
    def build_vocabulary(self, sentences: List[str]):
        """Build vocabulary from sentences for slot filling"""
        for sentence in sentences:
            words = sentence.lower().split()
            pos_tags = self._estimate_pos_tags(words)
            
            for word, pos in zip(words, pos_tags):
                if pos in ['VERB', 'NOUN', 'ADJ']:
                    self.vocabulary[pos].append(word)
        
        # Remove duplicates
        for pos in self.vocabulary:
            self.vocabulary[pos] = list(set(self.vocabulary[pos]))
    
    def fill_template(self, pattern: str) -> str:
        """Fill a pattern template with vocabulary"""
        filled = pattern
        
        # Replace [VERB], [NOUN], [ADJ] with random words from vocabulary
        for pos in ['VERB', 'NOUN', 'ADJ']:
            while f"[{pos}]" in filled:
                if self.vocabulary[pos]:
                    replacement = random.choice(self.vocabulary[pos])
                    filled = filled.replace(f"[{pos}]", replacement, 1)
                else:
                    # Fallback generic words
                    fallbacks = {
                        'VERB': ['create', 'build', 'develop', 'make'],
                        'NOUN': ['system', 'model', 'data', 'project'],
                        'ADJ': ['good', 'new', 'better', 'advanced']
                    }
                    replacement = random.choice(fallbacks[pos])
                    filled = filled.replace(f"[{pos}]", replacement, 1)
        
        return filled.capitalize()
    
    def generate_from_templates(self, sentences: List[str], num_generations: int = 5) -> List[str]:
        """Generate new sentences using template-based approach"""
        # Reset vocabulary to avoid cross-row contamination
        self.vocabulary.clear()
        # Build vocabulary strictly from provided sentences
        self.build_vocabulary(sentences)
        
        # Extract patterns
        patterns = self.extract_patterns(sentences)
        
        generated = []
        for _ in range(num_generations):
            if patterns:
                pattern = random.choice(patterns)
                new_sentence = self.fill_template(pattern)
                generated.append(new_sentence)
        
        return generated