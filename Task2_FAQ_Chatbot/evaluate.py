"""
Evaluation Benchmark Script for Task 2: FAQ Chatbot
Tests a curated set of test variations against the FAQ corpus and calculates accuracy metrics.
"""

from src.bot_engine import FAQBotEngine


def run_evaluation():
    engine = FAQBotEngine()

    test_cases = [
        # (user_query, expected_faq_id)
        ("Where is my package right now?", 1),
        ("I need to trace my delivery", 1),
        ("Can I cancel my recent purchase?", 2),
        ("I want to change the delivery address", 2),
        ("How many days will shipping take?", 3),
        ("Do you deliver within 2 days?", 3),
        ("Can you deliver to Europe or Japan?", 4),
        ("Do you ship abroad?", 4),
        ("What is your refund and return policy?", 5),
        ("Can I send back an unused shirt?", 5),
        ("When will my money be returned to my card?", 6),
        ("How long does a refund take?", 6),
        ("Can I pay using Apple Pay or PayPal?", 7),
        ("Do you accept Visa cards?", 7),
        ("Is it safe to enter my credit card info?", 8),
        ("Are transactions encrypted?", 8),
        ("I forgot my password, how to reset?", 9),
        ("Can't login to my account", 9),
        ("How to change my profile email address?", 10),
        ("Update phone number in settings", 10),
        ("I want to speak with a human customer support agent", 11),
        ("What is your support email and phone number?", 11),
        ("Where can I enter my discount promo code?", 12),
        ("Coupon is not applying at checkout", 12),
    ]

    total = len(test_cases)
    correct = 0
    high_conf_correct = 0
    total_confidence = 0.0

    print("=" * 70)
    print("           FAQ CHATBOT ACCURACY & SIMILARITY BENCHMARK           ")
    print("=" * 70)

    for query, expected_id in test_cases:
        res = engine.process_message(query)
        matched_id = res.get("faq_id")
        conf = res.get("confidence", 0.0)
        total_confidence += conf

        is_match = (matched_id == expected_id)
        if is_match:
            correct += 1
            if res.get("status") == "high_confidence":
                high_conf_correct += 1
            status_symbol = "PASS"
        else:
            status_symbol = "FAIL"

        print(f"[{status_symbol}] Query: '{query}'")
        print(f"         Expected ID: {expected_id} | Got: {matched_id} | Conf: {conf:.2f} | Status: {res.get('status')}")

    accuracy = (correct / total) * 100
    avg_conf = (total_confidence / total)

    print("=" * 70)
    print("BENCHMARK SUMMARY RESULTS:")
    print(f"  * Total Test Queries:        {total}")
    print(f"  * Correctly Matched FAQs:    {correct}/{total} ({accuracy:.1f}%)")
    print(f"  * High Confidence Matches:   {high_conf_correct}/{total} ({(high_conf_correct/total)*100:.1f}%)")
    print(f"  * Average Confidence Score:  {avg_conf:.3f}")
    print("=" * 70)

    return accuracy


if __name__ == "__main__":
    run_evaluation()
