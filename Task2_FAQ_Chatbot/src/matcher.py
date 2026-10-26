"""
FAQ Matcher Module using TF-IDF and Cosine Similarity
Matches user questions against the indexed FAQ corpus with content-token gating.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from .nlp_preprocessor import NLPPreprocessor
except ImportError:
    from nlp_preprocessor import NLPPreprocessor


class FAQMatcher:
    def __init__(self, data_path: Optional[str] = None):
        self.preprocessor = NLPPreprocessor()
        if data_path is None:
            data_path = str(Path(__file__).parent.parent / "data" / "faqs.json")
        self.data_path = data_path
        self.faqs: List[Dict[str, Any]] = []
        self.corpus_entries: List[Dict[str, Any]] = []
        self.processed_corpus: List[str] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.load_corpus()

    def load_corpus(self):
        """Loads and indexes FAQ questions, patterns, and tags."""
        with open(self.data_path, "r", encoding="utf-8") as f:
            self.faqs = json.load(f)

        self.corpus_entries = []
        self.processed_corpus = []

        for faq in self.faqs:
            # 1. Canonical question
            proc_q = self.preprocessor.preprocess(faq["question"])
            content_q = set(self.preprocessor.extract_content_tokens(faq["question"]))
            self.corpus_entries.append({
                "faq_id": faq["id"],
                "text": faq["question"],
                "type": "canonical",
                "faq": faq,
                "content_tokens": content_q
            })
            self.processed_corpus.append(proc_q)

            # 2. Alternative patterns
            for pat in faq.get("patterns", []):
                proc_pat = self.preprocessor.preprocess(pat)
                content_pat = set(self.preprocessor.extract_content_tokens(pat))
                self.corpus_entries.append({
                    "faq_id": faq["id"],
                    "text": pat,
                    "type": "pattern",
                    "faq": faq,
                    "content_tokens": content_pat
                })
                self.processed_corpus.append(proc_pat)

            # 3. Tags as keywords
            if faq.get("tags"):
                tag_text = " ".join(faq["tags"])
                proc_tags = self.preprocessor.preprocess(tag_text)
                content_tags = set(self.preprocessor.extract_content_tokens(tag_text))
                self.corpus_entries.append({
                    "faq_id": faq["id"],
                    "text": tag_text,
                    "type": "tags",
                    "faq": faq,
                    "content_tokens": content_tags
                })
                self.processed_corpus.append(proc_tags)

        # Train TF-IDF Vectorizer
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            token_pattern=r"(?u)\b\w+\b"
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.processed_corpus)
        return self.faqs

    def build_index(self):
        """Re-indexes the corpus and rebuilds the TF-IDF vector space."""
        return self.load_corpus()

    def match(self, user_query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Finds the most relevant FAQ for the given user query with deep neural telemetry.
        """
        import time
        start_time = time.perf_counter()

        processed_query = self.preprocessor.preprocess(user_query)
        query_content_tokens = set(self.preprocessor.extract_content_tokens(user_query))

        if not processed_query.strip():
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "matched": False,
                "confidence": 0.0,
                "status": "empty_query",
                "best_faq": None,
                "answer": None,
                "alternatives": [],
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "cos_score": 0.0,
                    "overlap_ratio": 0.0,
                    "overlap_tokens": [],
                    "top_terms": [],
                    "formula": "N/A"
                }
            }

        # Compute TF-IDF Cosine Similarity
        query_vec = self.vectorizer.transform([processed_query])
        cosine_sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Extract active query TF-IDF terms
        feature_names = self.vectorizer.get_feature_names_out()
        coo = query_vec.tocoo()
        top_terms = sorted(
            [{"term": feature_names[col], "weight": round(float(val), 4)} for col, val in zip(coo.col, coo.data)],
            key=lambda x: x["weight"],
            reverse=True
        )[:6]

        faq_scores: Dict[int, Dict[str, Any]] = {}
        for idx, cos_score in enumerate(cosine_sims):
            entry = self.corpus_entries[idx]
            faq_id = entry["faq_id"]

            doc_content = entry["content_tokens"]
            if query_content_tokens and doc_content:
                overlap_count = len(query_content_tokens.intersection(doc_content))
                overlap_ratio = overlap_count / float(len(query_content_tokens))
                overlap_tokens = list(query_content_tokens.intersection(doc_content))
            else:
                overlap_count = 0
                overlap_ratio = 0.0
                overlap_tokens = []

            # Content gating: If user asked a content question but zero content tokens match the FAQ, penalize
            if query_content_tokens and overlap_count == 0:
                final_score = cos_score * 0.15
            else:
                final_score = (0.70 * cos_score) + (0.30 * overlap_ratio)

            if faq_id not in faq_scores or final_score > faq_scores[faq_id]["score"]:
                faq_scores[faq_id] = {
                    "score": float(final_score),
                    "cos_score": float(cos_score),
                    "overlap_ratio": float(overlap_ratio),
                    "overlap_tokens": overlap_tokens,
                    "matched_pattern": entry["text"],
                    "faq": entry["faq"]
                }

        ranked_faqs = sorted(faq_scores.values(), key=lambda x: x["score"], reverse=True)
        latency_ms = (time.perf_counter() - start_time) * 1000

        if not ranked_faqs or ranked_faqs[0]["score"] < 0.20:
            # Fallback with sample popular questions
            alternatives = [
                {"id": f["id"], "question": f["question"], "category": f["category"]}
                for f in self.faqs[:3]
            ]
            return {
                "matched": False,
                "confidence": round(ranked_faqs[0]["score"], 4) if ranked_faqs else 0.0,
                "status": "no_match",
                "best_faq": None,
                "matched_pattern": None,
                "answer": None,
                "alternatives": alternatives,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "cos_score": round(ranked_faqs[0]["cos_score"], 4) if ranked_faqs else 0.0,
                    "overlap_ratio": round(ranked_faqs[0]["overlap_ratio"], 4) if ranked_faqs else 0.0,
                    "overlap_tokens": ranked_faqs[0]["overlap_tokens"] if ranked_faqs else [],
                    "top_terms": top_terms,
                    "formula": "Score < 0.20 Threshold (Fallback Engaged)",
                    "vector_dimension": self.tfidf_matrix.shape[1],
                    "corpus_entries_scanned": len(self.corpus_entries)
                }
            }

        best = ranked_faqs[0]
        confidence = round(best["score"], 4)

        alternatives = []
        for item in ranked_faqs[1:top_k + 1]:
            if item["score"] >= 0.18:
                alternatives.append({
                    "id": item["faq"]["id"],
                    "question": item["faq"]["question"],
                    "category": item["faq"]["category"],
                    "confidence": round(item["score"], 4)
                })

        status = "high_confidence" if confidence >= 0.38 else "moderate_confidence"

        return {
            "matched": True,
            "confidence": confidence,
            "status": status,
            "best_faq": best["faq"],
            "matched_pattern": best["matched_pattern"],
            "answer": best["faq"]["answer"],
            "alternatives": alternatives,
            "telemetry": {
                "latency_ms": round(latency_ms, 2),
                "cos_score": round(best["cos_score"], 4),
                "overlap_ratio": round(best["overlap_ratio"], 4),
                "overlap_tokens": best["overlap_tokens"],
                "top_terms": top_terms,
                "formula": f"0.70 × {best['cos_score']:.3f} (Cosine) + 0.30 × {best['overlap_ratio']:.3f} (Tokens) = {best['score']:.3f}",
                "vector_dimension": self.tfidf_matrix.shape[1],
                "corpus_entries_scanned": len(self.corpus_entries)
            }
        }

    def predictive_suggest(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Futuristic predictive search for live autocomplete HUD.
        Matches prefix, keywords, and semantic tokens with sub-millisecond response.
        """
        q = (query or "").strip().lower()
        if not q or len(q) < 2:
            return []

        suggestions: List[Dict[str, Any]] = []
        seen_ids = set()

        # 1. Exact or prefix match on canonical question
        for faq in self.faqs:
            q_lower = faq["question"].lower()
            if q in q_lower:
                suggestions.append({
                    "id": faq["id"],
                    "question": faq["question"],
                    "category": faq["category"],
                    "match_type": "Question",
                    "score": 0.95 if q_lower.startswith(q) else 0.85
                })
                seen_ids.add(faq["id"])

        # 2. Check patterns and tags
        for faq in self.faqs:
            if faq["id"] in seen_ids:
                continue
            for pat in faq.get("patterns", []):
                if q in pat.lower():
                    suggestions.append({
                        "id": faq["id"],
                        "question": faq["question"],
                        "category": faq["category"],
                        "match_type": f"Matches '{pat}'",
                        "score": 0.80
                    })
                    seen_ids.add(faq["id"])
                    break

            if faq["id"] not in seen_ids and any(q in t.lower() for t in faq.get("tags", [])):
                suggestions.append({
                    "id": faq["id"],
                    "question": faq["question"],
                    "category": faq["category"],
                    "match_type": "Tag Match",
                    "score": 0.70
                })
                seen_ids.add(faq["id"])

        # Sort by score and limit
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:limit]



if __name__ == "__main__":
    matcher = FAQMatcher()
    queries = [
        "Where is my package right now?",
        "Do you take Paypal?",
        "I need a refund for my damaged item",
        "How can I talk to an actual human customer representative?",
        "What is the weather in Paris?",
        "Hello!"
    ]
    for q in queries:
        res = matcher.match(q)
        print(f"Query: '{q}'")
        print(f"Matched: {res['matched']}, Status: {res['status']}, Confidence: {res['confidence']}")
        if res['best_faq']:
            print(f"FAQ: {res['best_faq']['question']}")
            print(f"Answer: {res['answer']}")
        print("=" * 60)
