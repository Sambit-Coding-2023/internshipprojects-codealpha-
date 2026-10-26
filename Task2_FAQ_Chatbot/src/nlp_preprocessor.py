"""
NLP Text Preprocessing Module for FAQ Chatbot
Handles cleaning, contraction expansion, tokenization, stopword removal, and lemmatization using NLTK.
"""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

CONTRACTIONS = {
    "can't": "cannot",
    "won't": "will not",
    "n't": " not",
    "'re": " are",
    "'s": " is",
    "'d": " would",
    "'ll": " will",
    "'t": " not",
    "'ve": " have",
    "'m": " am",
    "what's": "what is",
    "where's": "where is",
    "how's": "how is",
}

class NLPPreprocessor:
    def __init__(self):
        try:
            self.stop_words = set(stopwords.words("english"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            self.stop_words = set(stopwords.words("english"))

        try:
            self.lemmatizer = WordNetLemmatizer()
        except LookupError:
            nltk.download("wordnet", quiet=True)
            self.lemmatizer = WordNetLemmatizer()

        # Specific question operator words
        self.question_words = {"how", "what", "where", "when", "why", "who", "which", "can", "do", "does", "is", "are"}

    def expand_contractions(self, text: str) -> str:
        text = text.lower()
        for contraction, expansion in CONTRACTIONS.items():
            text = text.replace(contraction, expansion)
        return text

    def clean_text(self, text: str) -> str:
        text = self.expand_contractions(text)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def tokenize(self, text: str) -> list[str]:
        cleaned = self.clean_text(text)
        try:
            tokens = word_tokenize(cleaned)
        except Exception:
            tokens = cleaned.split()
        return tokens

    def extract_content_tokens(self, text: str) -> list[str]:
        """Extracts strictly content-bearing words (excluding all general stopwords and question operators)."""
        tokens = self.tokenize(text)
        content_tokens = []
        for t in tokens:
            if t not in self.stop_words and t not in self.question_words and len(t) > 1:
                lemma = self.lemmatizer.lemmatize(t, pos="v")
                lemma = self.lemmatizer.lemmatize(lemma, pos="n")
                content_tokens.append(lemma)
        return content_tokens

    def lemmatize_tokens(self, tokens: list[str]) -> list[str]:
        """Lemmatizes a list of token strings with dual verb and noun reduction."""
        res = []
        for token in tokens:
            lemma = self.lemmatizer.lemmatize(token, pos="v")
            lemma = self.lemmatizer.lemmatize(lemma, pos="n")
            res.append(lemma)
        return res

    def preprocess(self, text: str, remove_stopwords: bool = True) -> str:
        tokens = self.tokenize(text)
        processed = []
        for token in tokens:
            if remove_stopwords and token in self.stop_words:
                continue
            lemma = self.lemmatizer.lemmatize(token, pos="v")
            lemma = self.lemmatizer.lemmatize(lemma, pos="n")
            processed.append(lemma)
        return " ".join(processed)

    def analyze_sentiment(self, text: str) -> dict:
        """
        Futuristic sentiment and urgency analyzer.
        Evaluates lexical emotional signals and customer urgency in real-time.
        """
        lower = text.lower()
        
        urgent_signals = [
            "urgent", "asap", "emergency", "immediately", "broken", "damaged",
            "stolen", "lost", "fraud", "hacked", "terrible", "worst", "angry",
            "furious", "unacceptable", "scam", "never received", "chargeback"
        ]
        positive_signals = [
            "thank", "thanks", "thx", "awesome", "great", "excellent", "love",
            "helpful", "perfect", "good", "appreciate", "wonderful", "amazing"
        ]
        inquisitive_signals = [
            "how", "what", "where", "when", "why", "can i", "is it", "explain",
            "tell me", "does it", "options", "difference", "status"
        ]

        urgent_hits = [w for w in urgent_signals if w in lower]
        pos_hits = [w for w in positive_signals if w in lower]
        inq_hits = [w for w in inquisitive_signals if w in lower]

        if urgent_hits:
            return {
                "sentiment": "urgent",
                "urgency_level": "HIGH",
                "signals": urgent_hits,
                "label": "High Urgency / Critical Priority",
                "icon": "⚠️"
            }
        elif pos_hits:
            return {
                "sentiment": "positive",
                "urgency_level": "NORMAL",
                "signals": pos_hits,
                "label": "Positive Sentiment",
                "icon": "✨"
            }
        elif inq_hits:
            return {
                "sentiment": "inquisitive",
                "urgency_level": "NORMAL",
                "signals": inq_hits,
                "label": "Inquisitive Inquiry",
                "icon": "🔍"
            }
        else:
            return {
                "sentiment": "neutral",
                "urgency_level": "NORMAL",
                "signals": [],
                "label": "Neutral / Direct Query",
                "icon": "⚡"
            }

    def detailed_analysis(self, text: str) -> dict:
        """Provides complete explainability telemetry of the NLP pipeline."""
        expanded = self.expand_contractions(text)
        cleaned = self.clean_text(text)
        tokens = self.tokenize(text)
        content_tokens = self.extract_content_tokens(text)
        preprocessed = self.preprocess(text)
        sentiment = self.analyze_sentiment(text)
        
        return {
            "raw_text": text,
            "expanded_text": expanded,
            "cleaned_text": cleaned,
            "tokens": tokens,
            "token_count": len(tokens),
            "content_tokens": content_tokens,
            "content_count": len(content_tokens),
            "lemmatized_str": preprocessed,
            "sentiment": sentiment
        }


# Module alias for interoperability
TextPreprocessor = NLPPreprocessor

