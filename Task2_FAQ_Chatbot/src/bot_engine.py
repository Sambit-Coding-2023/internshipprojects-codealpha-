"""
Bot Engine for Task 2: FAQ Chatbot
Orchestrates intent classification (conversational greetings/goodbyes vs FAQ lookup)
and formats user-friendly responses.
"""

import random
from typing import Any, Dict, List, Optional
try:
    from .matcher import FAQMatcher
    from .knowledge_engine import UniversalKnowledgeEngine
    from .creator_engine import CreatorEngine
except ImportError:
    from matcher import FAQMatcher
    from knowledge_engine import UniversalKnowledgeEngine
    from creator_engine import CreatorEngine


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
        self.knowledge_engine = UniversalKnowledgeEngine()
        self.creator_engine = CreatorEngine()
        self.categories = sorted(list({faq["category"] for faq in self.matcher.faqs}))

    def get_categories(self) -> List[str]:
        return self.categories

    def get_all_faqs(self) -> List[Dict[str, Any]]:
        return self.matcher.faqs

    def get_suggestions(self, prefix: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Provides instant predictive suggestions for the live autocomplete HUD."""
        return self.matcher.predictive_suggest(prefix, limit=limit)

    def _get_action_widget(self, faq_id: Optional[int], raw_text: str) -> Optional[Dict[str, Any]]:
        """Generates dynamic interactive action cards for relevant customer support queries."""
        if faq_id == 1:
            return {
                "type": "order_tracker",
                "title": "Live Shipment Tracking",
                "tracking_code": "TRK-984210-US",
                "status": "In Transit - Out for Delivery",
                "eta": "Tomorrow by 2:00 PM",
                "carrier": "Express Priority Mail",
                "checkpoints": [
                    {"label": "Order Placed & Confirmed", "time": "Oct 28, 09:12 AM", "done": True},
                    {"label": "Packaged & Dispatched", "time": "Oct 28, 02:30 PM", "done": True},
                    {"label": "In Transit to Regional Distribution Hub", "time": "Oct 29, 04:15 AM", "active": True},
                    {"label": "Out for Delivery to Address", "time": "Oct 30, 02:00 PM", "pending": True}
                ]
            }
        elif faq_id == 2:
            return {
                "type": "order_modify",
                "title": "Order Management Portal",
                "order_id": "ORD-892401",
                "window_remaining": "45 minutes remaining in edit window",
                "actions": ["Update Delivery Address", "Cancel Order", "Modify Item Size/Color"]
            }
        elif faq_id == 3:
            return {
                "type": "shipping_calc",
                "title": "Shipping Methods & Estimates",
                "tiers": [
                    {"name": "Standard Shipping", "time": "3-5 Business Days", "cost": "Free over $50 ($4.99 under)"},
                    {"name": "Priority Express", "time": "1-2 Business Days", "cost": "$9.99"},
                    {"name": "Same-Day Courier", "time": "Delivered by 7 PM today", "cost": "$14.99"}
                ]
            }
        elif faq_id in (5, 6):
            return {
                "type": "return_rma",
                "title": "Online Return & Refund Portal",
                "rma_code": "RMA-77401-RET",
                "policy_window": "30-Day Hassle-Free Returns",
                "refund_eta": "3-5 Business Days to Original Card",
                "action_label": "Download Prepaid Return Shipping Label (PDF)"
            }
        elif faq_id in (7, 8):
            return {
                "type": "security_shield",
                "title": "Payment Security & Protection",
                "encryption": "256-Bit SSL / TLS 1.3 Encryption",
                "pci_dss": "PCI-DSS Level 1 Certified",
                "tokenization": "Zero Card Retention Vault",
                "verified": True
            }
        elif faq_id == 9:
            return {
                "type": "security_reset",
                "title": "Secure Password Reset",
                "security_level": "Encrypted Email Link (Valid 24h)",
                "action_label": "Send Password Reset Link to Email"
            }
        elif faq_id == 11:
            return {
                "type": "live_uplink",
                "title": "Contact Customer Support",
                "channel": "24/7 Live Support Desk",
                "queue_position": 1,
                "estimated_wait": "Under 1 minute",
                "rep_name": "Sarah M. (Customer Care Specialist)",
                "phone": "1-800-555-0199 (Toll-Free)",
                "email": "support@example.com"
            }
        elif faq_id == 12:
            return {
                "type": "promo_code",
                "title": "Available Promotional Coupons",
                "codes": [
                    {"code": "WELCOME15", "discount": "15% OFF", "description": "Valid on your first order"},
                    {"code": "FREESHIP", "discount": "FREE SHIPPING", "description": "Free standard shipping on any order"}
                ]
            }
        elif faq_id == 13:
            return {
                "type": "return_rma",
                "title": "Damaged Item Claim Center",
                "rma_code": "CLM-44102-DMG",
                "policy_window": "Free Replacement Guaranteed",
                "action_label": "Upload Photos & Request Instant Replacement"
            }
        elif faq_id == 14:
            return {
                "type": "return_rma",
                "title": "Fast Size & Color Exchange",
                "rma_code": "EXC-88204-SWAP",
                "policy_window": "30-Day Free Exchanges",
                "action_label": "Select Replacement Size / Color (Prepaid Label Included)"
            }
        elif faq_id == 16:
            return {
                "type": "promo_code",
                "title": "Gift Card Balance & Redemption",
                "codes": [
                    {"code": "GIFT-16-DIGIT", "discount": "STORE CREDIT", "description": "Enter in payment checkout"}
                ]
            }
        elif faq_id == 17:
            return {
                "type": "promo_code",
                "title": "Verified Student & Military Discount",
                "codes": [
                    {"code": "STUDENT15", "discount": "15% OFF", "description": "Verified via UNiDAYS / ID.me"}
                ]
            }
        elif faq_id == 19:
            return {
                "type": "security_shield",
                "title": "Cryptocurrency Payments",
                "encryption": "BitPay & Coinbase Web3 Checkout",
                "pci_dss": "Zero Gas Fees on Native Transfers",
                "tokenization": "Bitcoin (BTC), Ethereum (ETH), USDC",
                "verified": True
            }
        elif faq_id == 25:
            return {
                "type": "security_shield",
                "title": "Two-Factor Authentication (2FA)",
                "encryption": "Time-based One-Time Password (TOTP)",
                "pci_dss": "RFC 6238 Compliant",
                "tokenization": "Google Authenticator / Authy",
                "verified": True
            }
        return None

    def process_message(self, message: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Processes a user message and returns a rich response object with telemetry.
        Orchestration order:
        1. Greetings, Farewells, Gratitude
        2. Real-time Math & Temporal Clock Lookup
        3. Technical, Coding, Science & Creative Query Recognition
        4. TF-IDF FAQ Vector Matching (with confidence threshold gating)
        5. Universal Knowledge Engine (Google Gemini AI, Wikipedia, DuckDuckGo)
        6. Graceful escalation fallback
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
                "Where is my package right now?",
                "What is your refund policy?",
                "Write Python code to reverse a list",
                "Why is the sky blue?"
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
            category_list = ", ".join(self.categories[:6])
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "help",
                "text": (
                    f"I can answer questions regarding any of our store topics, or ANY open-world knowledge:\n\n"
                    f"• **Store Support**: Orders, Shipping, Returns, Payments, Account, Loyalty, Subscriptions\n"
                    f"• **AI & Coding**: Python, JavaScript, SQL, CSS, Git, Algorithms, Regex\n"
                    f"• **Science & Facts**: Physics, Biology, Internet, Math Calculations, Wikipedia Knowledge\n\n"
                    f"Try asking:\n"
                    f"• 'Where is my package right now?'\n"
                    f"• 'Write Python code to reverse a list'\n"
                    f"• 'Why is the sky blue?'\n"
                    f"• 'What is 15% of 350?'"
                ),
                "confidence": 1.0,
                "categories": self.categories,
                "suggestions": [
                    "Where is my package right now?",
                    "What is your return policy?",
                    "Write Python code to reverse a list",
                    "Explain Quantum Computing"
                ],
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "intent": "Help & Directory",
                    "nlp_data": nlp_data,
                    "formula": "Deterministic Intent Rule"
                }
            }

        # 4b. Instant Calculation & Real-time Clock Check
        math_ans = self.knowledge_engine.answer_math(raw_text)
        if math_ans:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "knowledge_match",
                "text": math_ans["text"],
                "category": math_ans.get("category", "Mathematics"),
                "canonical_question": raw_text,
                "confidence": 1.0,
                "status": "exact_match",
                "source": math_ans.get("source", "Safe Math Engine"),
                "badge": math_ans.get("badge", "CALCULATION"),
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "engine": "Safe AST Math Evaluator",
                    "formula": "Deterministic Arithmetic AST",
                    "nlp_data": nlp_data
                }
            }

        dt_ans = self.knowledge_engine.answer_datetime(raw_text)
        if dt_ans:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "knowledge_match",
                "text": dt_ans["text"],
                "category": dt_ans.get("category", "Utility"),
                "canonical_question": raw_text,
                "confidence": 1.0,
                "status": "exact_match",
                "source": dt_ans.get("source", "System Clock"),
                "badge": dt_ans.get("badge", "TIME & DATE"),
                "alternatives": [],
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "engine": "Real-time System Clock",
                    "formula": "System Temporal Lookup",
                    "nlp_data": nlp_data
                }
            }

        sample_alternatives = [
            {"id": f["id"], "question": f["question"], "category": f["category"]}
            for f in self.matcher.faqs[:4]
        ]

        # 4c. Creator Engine (AI Images, PowerPoint Presentations, PDF Documents)
        if self.creator_engine.can_handle(raw_text):
            create_res = self.creator_engine.process(raw_text, api_key=api_key)
            if create_res:
                latency_ms = (time.perf_counter() - start_time) * 1000
                create_res["telemetry"] = {
                    "latency_ms": round(latency_ms, 2),
                    "engine": create_res.get("badge", "Creator Engine"),
                    "formula": "Generative Artifact Synthesis",
                    "nlp_data": nlp_data
                }
                create_res["alternatives"] = sample_alternatives
                create_res["sentiment"] = sentiment
                return create_res

        # 4d. Technical, Coding, Science & Explicit Encyclopedic Queries
        if self.knowledge_engine.is_technical_or_creative_query(raw_text) or self.knowledge_engine.is_encyclopedic_query(raw_text):
            k_ans = self.knowledge_engine.answer(raw_text, api_key=api_key)
            if k_ans and k_ans.get("found"):
                latency_ms = (time.perf_counter() - start_time) * 1000
                return {
                    "type": "knowledge_match",
                    "text": k_ans["text"],
                    "category": k_ans.get("category", "General Knowledge"),
                    "canonical_question": k_ans.get("title", raw_text),
                    "confidence": 0.98,
                    "status": "knowledge_verified",
                    "source": k_ans.get("source", "Universal Knowledge Engine"),
                    "badge": k_ans.get("badge", "AI KNOWLEDGE"),
                    "url": k_ans.get("url"),
                    "alternatives": sample_alternatives,
                    "sentiment": sentiment,
                    "telemetry": {
                        "latency_ms": round(latency_ms, 2),
                        "engine": k_ans.get("source", "Knowledge Engine"),
                        "formula": "High-IQ Domain Recognition",
                        "nlp_data": nlp_data
                    }
                }

        # 5. FAQ Matching via TF-IDF & Cosine Similarity
        match_res = self.matcher.match(raw_text)
        latency_ms = (time.perf_counter() - start_time) * 1000

        telemetry = match_res.get("telemetry", {})
        telemetry["latency_ms"] = round(latency_ms, 2)
        telemetry["nlp_data"] = nlp_data

        if match_res["matched"]:
            confidence = match_res["confidence"]

            # If confidence is lower than 0.52 (potential false positive on common words like 'write' or 'code'),
            # verify if the knowledge engine has a better open-domain answer first.
            if confidence < 0.52:
                k_ans = self.knowledge_engine.answer(raw_text, api_key=api_key)
                if k_ans and k_ans.get("found"):
                    return {
                        "type": "knowledge_match",
                        "text": k_ans["text"],
                        "category": k_ans.get("category", "General Knowledge"),
                        "canonical_question": k_ans.get("title", raw_text),
                        "confidence": 0.95,
                        "status": "knowledge_verified",
                        "source": k_ans.get("source", "Universal Knowledge Engine"),
                        "badge": k_ans.get("badge", "AI KNOWLEDGE"),
                        "url": k_ans.get("url"),
                        "alternatives": sample_alternatives,
                        "sentiment": sentiment,
                        "telemetry": {
                            "latency_ms": round(latency_ms, 2),
                            "engine": k_ans.get("source", "Knowledge Engine"),
                            "formula": "Open-Domain Knowledge Override",
                            "nlp_data": nlp_data
                        }
                    }

            best_faq = match_res["best_faq"]
            status = match_res["status"]

            if status == "high_confidence":
                reply = best_faq["answer"]
            else:
                reply = (
                    f"Based on your question, here is what might help:\n\n"
                    f"{best_faq['answer']}"
                )

            # Check if this query qualifies for an interactive action widget
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

        # 6. Universal Knowledge Engine (Gemini AI, Wikipedia, DuckDuckGo, Chit-Chat)
        k_ans = self.knowledge_engine.answer(raw_text, api_key=api_key)
        if k_ans and k_ans.get("found"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "type": "knowledge_match",
                "text": k_ans["text"],
                "category": k_ans.get("category", "General Knowledge"),
                "canonical_question": k_ans.get("title", raw_text),
                "confidence": 0.95,
                "status": "knowledge_verified",
                "source": k_ans.get("source", "Universal Knowledge Engine"),
                "badge": k_ans.get("badge", "AI KNOWLEDGE"),
                "url": k_ans.get("url"),
                "alternatives": sample_alternatives,
                "sentiment": sentiment,
                "telemetry": {
                    "latency_ms": round(latency_ms, 2),
                    "engine": k_ans.get("source", "Knowledge Engine"),
                    "formula": "Open-Domain Knowledge Retrieval",
                    "nlp_data": nlp_data
                }
            }

        # 7. Fallback if no matching FAQ or knowledge was found
        return {
            "type": "fallback",
            "text": (
                "I'm sorry, I couldn't find a definitive answer for that in our FAQ knowledgebase or general encyclopedia. "
                "You can try rephrasing with key terms, or connect with our 24/7 customer support specialist below."
            ),
            "confidence": match_res.get("confidence", 0.0),
            "status": "unmatched",
            "alternatives": sample_alternatives,
            "action_widget": {
                "type": "live_uplink",
                "title": "Contact Customer Support",
                "channel": "Customer Support Desk",
                "queue_position": 1,
                "estimated_wait": "Under 1 minute",
                "rep_name": "Customer Care Specialist",
                "phone": "1-800-555-0199",
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
