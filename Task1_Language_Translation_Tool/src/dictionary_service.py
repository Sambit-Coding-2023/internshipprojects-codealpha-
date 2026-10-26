"""
Dictionary & Word Lookup Service
Fetches definitions, parts of speech, phonetic transcriptions, and synonyms for single terms.
"""

from typing import Any, Dict, List, Optional
import requests


class DictionaryService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def lookup(self, word: str) -> Optional[Dict[str, Any]]:
        """Look up definitions, phonetics, and meanings for a word."""
        clean = word.strip().lower()
        if not clean or " " in clean or len(clean) > 30:
            return None

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{clean}"
        try:
            resp = self.session.get(url, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    entry = data[0]
                    phonetic = entry.get("phonetic", "")
                    meanings = []
                    for m in entry.get("meanings", [])[:3]:
                        part = m.get("partOfSpeech", "")
                        defs = [d.get("definition") for d in m.get("definitions", [])[:2] if d.get("definition")]
                        synonyms = m.get("synonyms", [])[:4]
                        meanings.append({
                            "partOfSpeech": part,
                            "definitions": defs,
                            "synonyms": synonyms
                        })

                    return {
                        "word": clean,
                        "phonetic": phonetic,
                        "meanings": meanings
                    }
        except Exception:
            pass

        return None
