from google import genai
import os
from typing import List, Dict
import logging
import time
import re
from dotenv import load_dotenv

class GeminiGenerator:
    def __init__(self, api_key: str = None, model_name="gemini-2.5-flash"):
        self.logger = self._setup_logging()
        try:
            load_dotenv()
        except Exception:
            pass
        
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = genai.Client()
        except Exception:
            self.client = genai.Client()

        self.model_name = model_name
        self.logger.info(f"✅ Gemini Generator initialized with {model_name}")
    
    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def generate_variations(self, text: str, num_variations: int = 3, style: str = "paraphrase") -> List[str]:
        """Generate variations of processed text using context-aware generation"""
        try:
            # The key insight: We need to understand WHAT the original text meant
            # before we can generate variations of the processed version
            
            # Step 1: Analyze what the processed text represents
            analysis_prompt = f"""
I have a text that has been processed through NLP preprocessing (lemmatization, stopword removal). 
The processed text is: "{text}"

Please analyze what the original meaning or sentence might have been before processing.
Focus on understanding the core semantic meaning and relationships between the words.

Based on your analysis, provide a brief description of the likely original meaning:
"""
            
            analysis_response = self.client.models.generate_content(
                model=self.model_name, 
                contents=analysis_prompt
            )
            
            analysis_text = self._extract_response_text(analysis_response)
            self.logger.info(f"Analysis of '{text}': {analysis_text[:100]}...")
            
            # Step 2: Generate variations based on the understood meaning, grounded in tokens
            tokens = [t for t in text.strip().split() if t]
            token_list = ", ".join(tokens)
            glue_words = (
                "the, a, an, to, of, and, or, over, under, on, in, at, by, for, with, "
                "is, are, was, were, be, been, being, that, which, who, as, into, from, "
                "up, down, out, about, between, through, this, it"
            )

            generation_prompt = f"""
I have a processed (tokenized/lemmatized) text: "{text}"
Analysis of its meaning: {analysis_text}

Now write {num_variations} natural, grammatical English sentences that:
1) Faithfully express the above meaning, and
2) Are strictly grounded in these content tokens: [{token_list}]

Hard constraints:
- Use each token exactly once (light inflection allowed: jump→jumps/jumped/jumping; dog→dogs; fox→foxes).
- You may add only minimal glue/functional words from this set: {glue_words}.
- Do NOT introduce new content words beyond inflections of the given tokens.
- Avoid duplication like "world world" or omitting any token.
- Return one sentence per line, no numbering or extra text.
"""
            
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=generation_prompt
            )

            text_output = self._extract_response_text(response)
            variations = self._parse_gemini_response(text_output)
            
            # Step 3: Strict quality filtering
            filtered_variations = []
            for variation in variations[:num_variations]:
                if self._is_high_quality_variation(text, variation):
                    filtered_variations.append(variation)
            
            time.sleep(1)  # Rate limiting
            return filtered_variations
            
        except Exception as e:
            self.logger.error(f"Error generating with Gemini: {e}")
            return []

    def _extract_response_text(self, response) -> str:
        """Extract text from Gemini response object"""
        try:
            if hasattr(response, 'text') and response.text:
                return response.text
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        return str(candidate.content.parts[0])
            
            return str(response)
        except Exception as e:
            self.logger.error(f"Error extracting response text: {e}")
            return ""

    def _is_high_quality_variation(self, original_processed: str, variation: str) -> bool:
        """Strict quality checking grounded in tokens: exact-once usage, minimal glue, sentence-like output."""
        if not variation or len(variation.strip()) < 8:
            return False

        v = variation.strip()
        if not v[0].isupper() or v[-1] not in ".!?":
            return False
        if len(v) > 300:
            return False

        # Normalize
        def norm_words(s: str) -> List[str]:
            s = re.sub(r"[^a-zA-Z\s]", " ", s.lower())
            return [w for w in s.split() if w]

        base_tokens = norm_words(original_processed)
        words = norm_words(variation)
        if not base_tokens or not words:
            return False

        glue = {"the","a","an","to","of","and","or","over","under","on","in","at","by","for","with","is","are","was","were","be","been","being","that","which","who","as","into","from","up","down","out","about","between","through","this","it"}

        # Light inflection matcher
        def match_inflect(word: str, base: str) -> bool:
            if word == base:
                return True
            for suf in ("s","es","ed","ing"):
                if word == base + suf:
                    return True
            if base.endswith("y") and word == base[:-1] + "ies":
                return True
            if base.endswith("s") and word == base[:-1]:
                return True
            return False

        # Count matches per token, track foreign content
        counts = {bt: 0 for bt in base_tokens}
        foreign = False
        for w in words:
            matched = False
            for bt in base_tokens:
                if match_inflect(w, bt):
                    counts[bt] += 1
                    matched = True
            if not matched and w not in glue:
                foreign = True

        exact_once = all(c == 1 for c in counts.values()) and len(counts) > 0
        if not exact_once or foreign:
            return False
            
        return True

    def _parse_gemini_response(self, response_text: str) -> List[str]:
        """Parse Gemini response to extract individual variations"""
        if not response_text:
            return []
            
        lines = response_text.strip().split('\n')
        variations = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove numbering, bullets, quotes
            line = re.sub(r'^[\d\-•]\.?\s*', '', line)
            line = line.strip('"\'')
            
            # Skip lines that are too short or look like instructions
            if (len(line) >= 10 and 
                line[0].isupper() and 
                not any(marker in line.lower() for marker in ['variation', 'sentence', 'example', 'note:'])):
                variations.append(line)
        
        return variations
    
    def generate_dataset_expansions(self, seed_texts: List[str], variations_per_text: int = 2) -> Dict[str, List[str]]:
        """Generate expanded dataset from seed texts"""
        results = {}
        
        for i, text in enumerate(seed_texts):
            self.logger.info(f"Generating variations for text {i+1}/{len(seed_texts)}: {text}")
            
            variations = self.generate_variations(text, variations_per_text)
            results[text] = variations
            
            if variations:
                self.logger.info(f"Generated {len(variations)} quality variations")
            else:
                self.logger.warning(f"No quality variations generated for: {text}")
            
            if (i + 1) % 3 == 0:  # More frequent updates since this is slower
                self.logger.info(f"Progress: {i+1}/{len(seed_texts)} texts processed")
        
        return results
    
    def validate_and_filter(self, original: str, generated: List[str]) -> List[str]:
        """Filter generated texts for quality"""
        return [text for text in generated if self._is_high_quality_variation(original, text)]

    def debug_generation_process(self, text: str):
        """Debug the generation process step by step"""
        print(f"\n🔍 DEBUGGING GENERATION FOR: '{text}'")
        print("=" * 50)
        
        # Step 1: Analysis
        analysis_prompt = f"""
I have a text that has been processed through NLP preprocessing (lemmatization, stopword removal). 
The processed text is: "{text}"

Please analyze what the original meaning or sentence might have been before processing.
Focus on understanding the core semantic meaning and relationships between the words.

Based on your analysis, provide a brief description of the likely original meaning:
"""
        
        print("1. Analysis Prompt:")
        print(analysis_prompt)
        
        analysis_response = self.client.models.generate_content(
            model=self.model_name, 
            contents=analysis_prompt
        )
        
        analysis_text = self._extract_response_text(analysis_response)
        print(f"\n2. Analysis Result: {analysis_text}")
        
        # Step 2: Generation
        generation_prompt = f"""
I have a processed text: "{text}"
After analysis, the core meaning appears to be: {analysis_text}

Now generate 2 natural, grammatical variations that preserve this core meaning.

Return only the variations, one per line.
"""
        
        print(f"\n3. Generation Prompt:")
        print(generation_prompt)
        
        response = self.client.models.generate_content(
            model=self.model_name, 
            contents=generation_prompt
        )

        raw_output = self._extract_response_text(response)
        print(f"\n4. Raw Gemini Output:")
        print(raw_output)
        
        variations = self._parse_gemini_response(raw_output)
        print(f"\n5. Parsed Variations: {variations}")
        
        filtered = self.validate_and_filter(text, variations)
        print(f"\n6. Final Filtered Variations: {filtered}")
        
        return filtered