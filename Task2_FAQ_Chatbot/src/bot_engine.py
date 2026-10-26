"""
Bot Engine for Task 2: FAQ Chatbot
Orchestrates intent classification (conversational greetings/goodbyes vs FAQ lookup)
and formats user-friendly responses.
"""

import random
from typing import Any, Dict, List, Optional
try:
    from .matcher import FAQMatcher
except ImportError:
    from matcher import FAQMatcher


GREETING_INPUTS = {
    "hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon",
    "good evening", "sup", "yo", "what's up", "howdy"
}

GREETING_RESPONSES = [
    "Hello! I am your AI Support Assistant. How can I help you today?",
    "Hi there! Welcome to support. Feel free to ask any question regarding orders, shipping, refunds, or payments.",
    "Greetings! How may I assist you with your purchases or account today?"
]

FAREWELL_INPUTS = {
    "bye", "goodbye", "see you", "cya", "farewell", "have a good day", "exit", "quit"
}

FAREWELL_RESPONSES = [
    "Goodbye! Let me know if you need anything else.",
    "Have a wonderful day! Happy shopping.",
    "Bye! Feel free to reach back out anytime you have questions."
]

GRATITUDE_INPUTS = {
    "thanks", "thank you", "thx", "appreciate it", "thank you so much", "perfect thanks"
}

GRATITUDE_RESPONSES = [
    "You're very welcome! Is there anything else I can help you with?",
    "Glad I could help! Let me know if you have other questions.",
    "Anytime! We're here 24/7."
]

HELP_INPUTS = {
    "help", "categories", "topics", "options", "menu", "what can you do", "features"
}


class FAQBotEngine:
    def __init__(self, data_path: Optional[str] = None):
        self.matcher = FAQMatcher(data_path=data_path)
        self.categories = sorted(list({faq["category"] for faq in self.matcher.faqs}))

    def get_categories(self) -> List[str]:
        return self.categories

    def get_all_faqs(self) -> List[Dict[str, Any]]:
        return self.matcher.faqs

    def get_suggestions(self, prefix: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Provides instant predictive suggestions for the live autocomplete HUD."""
        return self.matcher.predictive_suggest(prefix, limit=limit)

    def _get_action_widget(self, faq_id: Optional[int], raw_text: str) -> Optional[Dict[str, Any]]:
        """Generates dynamic interactive holographic action widgets based on intent."""
        if faq_id == 1:
            return {
                "type": "order_tracker",
                "title": "Quantum Transit Radar",
                "tracking_code": "CYBER-8924-X",
                "status": "In Sub-Orbital Transit",
                "eta": "Tomorrow, 14:00 UTC",
                "carrier": "NeuralExpress Global",
                "checkpoints": [
                    {"label": "Order Placed & Verified", "time": "Yesterday, 09:12", "done": True},
                    {"label": "Neural Hub Packaging", "time": "Yesterday, 14:30", "done": True},
                    {"label": "Sub-Orbital Air Transit", "time": "Today, 03:45", "active": True},
                    {"label": "Local Hub & Out for Delivery", "time": "Tomorrow, 14:00", "pending": True}
                ]
            }
        elif faq_id == 2:
            return {
                "type": "order_modify",
                "title": "Order Modification Terminal",
                "order_id": "ORD-99412",
                "window_remaining": "48 minutes remaining in edit window",
                "actions": ["Update Delivery Address", "Cancel Order", "Swap Size/Color"]
            }
        elif faq_id == 3:
            return {
                "type": "shipping_calc",
                "title": "Quantum Shipping Matrix",
                "tiers": [
                    {"name": "Standard Hyper-Ground", "time": "3-5 Business Days", "cost": "Free over $50"},
                    {"name": "Priority Atmospheric Flight", "time": "1-2 Business Days", "cost": "$9.99"},
                    {"name": "Same-Day Cyber Courier", "time": "< 6 Hours", "cost": "$19.99"}
                ]
            }
        elif faq_id in (5, 6):
            return {
                "type": "return_rma",
                "title": "Instant RMA Return Terminal",
                "rma_code": "RMA-7740-REFUND",
                "policy_window": "30 Days Hassle-Free",
                "refund_eta": "3-5 Business Days to Original Card",
                "action_label": "Generate Digital QR Return Label"
            }
        elif faq_id in (7, 8):
            return {
                "type": "security_shield",
                "title": "Quantum Security Protocol",
                "encryption": "AES-256 GCM + SHA-384",
                "pci_dss": "Level 1 Certified Compliant",
                "tokenization": "Zero Card Retention Vault",
                "verified": True
            }
        elif faq_id == 9:
            return {
                "type": "security_reset",
                "title": "Neural Password Reset Link",
                "security_level": "Biometric + OTP 2FA",
                "action_label": "Trigger Instant One-Time Reset Link"
            }
        elif faq_id == 11:
            return {
                "type": "live_uplink",
                "title": "Human Operator Uplink Console",
                "channel": "Live Support Bridge",
                "queue_position": 1,
                "estimated_wait": "25 seconds",
                "rep_name": "Agent Sarah M. (Senior Care Specialist)",
                "phone": "1-800-555-CYBER",
                "email": "support@example.com"
            }
        elif faq_id == 12:
            return {
                "type": "promo_code",
                "title": "Cyber Discount Vault",
                "codes": [
                    {"code": "NEURAL20", "discount": "20% OFF", "description": "Applied across entire catalog"},
                    {"code": "CYBERSHIP", "discount": "FREE EXPRESS", "description": "Free 1-Day Atmospheric Transit"}
                ]
            }
        return None

    def process_message(self, message: str) -> Dict[str, Any]:
        """
        Processes a user message and returns a rich response object with telemetry.
        """
        import time
        start_time = time.perf_counter()

        raw_text = (message or "").strip()
        lower_text = raw_text.lower().rstrip("!?. ")

        if not raw_text:
            return {
                "type": "error",
                "text": "Please type a question so I can assist you.",
                "confidence": 0.0,
                "alternatives": [],
                "telemetry": {
                    "latency_ms": 0.1,
                    "formula": "Empty input"
                }
            }

        nlp_data = self.matcher.preprocessor.detailed_analysis(raw_text)
        sentiment = nlp_data.get("sentiment", {})

        # 1. Greetings
        if lower_text in GREETING_INPUTS:
            sample_questions = [
                "How do I track my order status?",
                "What is your refund policy?",
                "What payment methods do you accept?"
            ]
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "greeting",
                "text": random.choice(GREETING_RESPONSES),
                "confidence": 1.0,
                "suggestions": sample_questions,
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "intent": "Conversational Greeting",
                    "nlp_data": nlp_data,
                    "formula": "Deterministic Intent Rule"
                }
            }

        # 2. Farewells
        if lower_text in FAREWELL_INPUTS:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "farewell",
                "text": random.choice(FAREWELL_RESPONSES),
                "confidence": 1.0,
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "intent": "Conversational Farewell",
                    "nlp_data": nlp_data,
                    "formula": "Deterministic Intent Rule"
                }
            }

        # 3. Gratitude
        if lower_text in GRATITUDE_INPUTS:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "gratitude",
                "text": random.choice(GRATITUDE_RESPONSES),
                "confidence": 1.0,
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "intent": "Conversational Gratitude",
                    "nlp_data": nlp_data,
                    "formula": "Deterministic Intent Rule"
                }
            }

        # 4. Help / Categories exploration
        if lower_text in HELP_INPUTS:
            category_list = ", ".join(self.categories)
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "help",
                "text": (
                    f"I can answer questions regarding any of the following categories:\n"
                    f"• {category_list}\n\n"
                    f"Try asking questions like:\n"
                    f"• 'Where is my order?'\n"
                    f"• 'Can I return an item?'\n"
                    f"• 'Do you accept Apple Pay?'\n"
                    f"• 'How do I reach a human representative?'"
                ),
                "confidence": 1.0,
                "categories": self.categories,
                "suggestions": [
                    "Where is my package?",
                    "How to get a refund?",
                    "What payment methods are supported?"
                ],
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "intent": "Help & Category Directory",
                    "nlp_data": nlp_data,
                    "formula": "Deterministic Intent Rule"
                }
            }

        # 5. FAQ Matching via TF-IDF & Cosine Similarity
        match_res = self.matcher.match(raw_text)
        latency_ms = (time.perf_counter() - start_time) * 1000

        telemetry = match_res.get("telemetry", {})
        telemetry["latency_ms"] = round(latency_ms, 2)
        telemetry["nlp_data"] = nlp_data

        if match_res["matched"]:
            best_faq = match_res["best_faq"]
            confidence = match_res["confidence"]
            status = match_res["status"]

            if status == "high_confidence":
                reply = best_faq["answer"]
            else:
                reply = (
                    f"Based on your question, here is what might help:\n\n"
                    f"{best_faq['answer']}"
                )

            # Check if this query qualifies for an interactive holographic action widget
            action_widget = self._get_action_widget(best_faq.get("id"), raw_text)

            return {
                "type": "faq_match",
                "text": reply,
                "faq_id": best_faq["id"],
                "category": best_faq["category"],
                "canonical_question": best_faq["question"],
                "confidence": confidence,
                "status": status,
                "alternatives": match_res.get("alternatives", []),
                "action_widget": action_widget,
                "sentiment": sentiment,
                "telemetry": telemetry
            }

        # 6. Fallback if no matching FAQ was found
        sample_alternatives = [
            {"id": f["id"], "question": f["question"], "category": f["category"]}
            for f in self.matcher.faqs[:4]
        ]
        return {
            "type": "fallback",
            "text": (
                "I'm sorry, I couldn't find an exact match for your question in our neural database. "
                "You can try rephrasing, ask about orders, shipping, refunds, or connect to human support."
            ),
            "confidence": match_res.get("confidence", 0.0),
            "status": "unmatched",
            "alternatives": sample_alternatives,
            "action_widget": {
                "type": "live_uplink",
                "title": "Human Operator Uplink Console",
                "channel": "Fallback Support Bridge",
                "queue_position": 1,
                "estimated_wait": "Instant Connect",
                "rep_name": "Customer Care Desk",
                "phone": "1-800-555-CYBER",
                "email": "support@example.com"
            },
            "sentiment": sentiment,
            "telemetry": telemetry
        }



if __name__ == "__main__":
    engine = FAQBotEngine()
    test_inputs = [
        "hi",
        "where is my package?",
        "what payment types are valid?",
        "how do i speak to support agent?",
        "can i cook pasta with this?",
        "thanks!"
    ]
    for inp in test_inputs:
        resp = engine.process_message(inp)
        print(f"User: {inp}")
        print(f"Bot [{resp['type']} | Conf: {resp['confidence']}]: {resp['text']}")
        print("=" * 60)
