"""
Command-Line Interface for Task 2: FAQ Chatbot
Run in terminal: python cli.py
"""

import sys
from src.bot_engine import FAQBotEngine


def run_cli():
    print("=" * 65)
    print("      AI FAQ SUPPORT CHATBOT (Task 2) - TERMINAL INTERFACE      ")
    print("=" * 65)
    print("Initializing NLP Preprocessor and TF-IDF matcher...")
    bot = FAQBotEngine()
    print("Bot ready! Type your questions below.")
    print("Commands: 'help' to see categories, 'exit' or 'quit' to close.")
    print("-" * 65)

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "q"}:
                print("Bot: Goodbye! Have a great day.")
                break

            response = bot.process_message(user_input)
            print(f"\nBot: {response['text']}")

            if response.get("canonical_question"):
                print(f"     [Category: {response['category']} | Matched: '{response['canonical_question']}' | Confidence: {response['confidence']:.2f}]")

            if response.get("alternatives"):
                print("\nRelated Questions:")
                for alt in response["alternatives"][:2]:
                    print(f"  • {alt['question']}")

            if response.get("suggestions"):
                print("\nSuggestions:")
                for sug in response["suggestions"]:
                    print(f"  • {sug}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    run_cli()
