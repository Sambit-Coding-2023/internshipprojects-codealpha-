import sys
import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")

# Configure UTF-8 for Windows terminal output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import argparse
from pathlib import Path


from src.languages import get_all_languages, get_language_name
from src.translator import TranslationService
from src.tts_service import TTSService


def run_cli():
    parser = argparse.ArgumentParser(
        description="AI Language Translation Tool (Task 1 CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python translate_cli.py "Hello, how are you today?" --target es
  python translate_cli.py "Bonjour le monde" --source fr --target en
  python translate_cli.py --file document.txt --target de
  python translate_cli.py --list-languages
  python translate_cli.py "Welcome to the studio" --target ja --tts
        """
    )

    parser.add_argument("text", nargs="?", default="", help="Text string to translate")
    parser.add_argument("-s", "--source", default="auto", help="Source language code (default: auto)")
    parser.add_argument("-t", "--target", default="es", help="Target language code (default: es)")
    parser.add_argument("-f", "--file", help="Path to text file to translate")
    parser.add_argument("--tts", action="store_true", help="Generate and save MP3 audio of the translation")
    parser.add_argument("--list-languages", action="store_true", help="Print all supported language codes")
    parser.add_argument("--detect-only", action="store_true", help="Only detect the language of the input text")

    args = parser.parse_args()

    if args.list_languages:
        print("\n" + "=" * 65)
        print("          SUPPORTED LANGUAGES (100+ GLOBAL CODES)")
        print("=" * 65)
        langs = get_all_languages()
        for idx, l in enumerate(langs, 1):
            flag = l.get("flag", "🌐")
            print(f" {l['code']:<6} | {flag} {l['name']:<24} ({l.get('native', '')})")
        print("=" * 65)
        return

    # Determine input text
    text_to_translate = args.text
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found at {args.file}")
            sys.exit(1)
        text_to_translate = file_path.read_text(encoding="utf-8")

    if not text_to_translate:
        print("\nInteractive AI Translation Mode (Type text and press Enter, or 'q' to exit):")
        translator = TranslationService()
        while True:
            try:
                line = input(f"\n[auto -> {args.target}] Enter text: ").strip()
                if not line or line.lower() == 'q':
                    print("Exiting.")
                    break
                res = translator.translate(line, source_lang=args.source, target_lang=args.target)
                print(f"-> [{res['target_lang'].upper()}]: {res['translated_text']}")
                print(f"   (Detected: {res['detected_lang_name']} | Engine: {res['engine_used']} | {res['latency_ms']}ms)")
            except KeyboardInterrupt:
                break
        return

    translator = TranslationService()

    if args.detect_only:
        detected_code, conf = translator.detect_language(text_to_translate)
        name = get_language_name(detected_code)
        print(f"\nDetected Language: {name} [{detected_code}] (Confidence: {conf * 100:.1f}%)")
        return

    print("\n" + "=" * 70)
    print("                AI LANGUAGE TRANSLATION STUDIO (CLI)                 ")
    print("=" * 70)
    print(f"Source Language:   {get_language_name(args.source)} [{args.source}]")
    print(f"Target Language:   {get_language_name(args.target)} [{args.target}]")
    print(f"Input Characters:  {len(text_to_translate)} ({len(text_to_translate.split())} words)")
    print("-" * 70)

    try:
        result = translator.translate(
            text=text_to_translate,
            source_lang=args.source,
            target_lang=args.target
        )

        print("\n--- ORIGINAL TEXT ---")
        print(text_to_translate)

        print("\n--- TRANSLATED TEXT ---")
        print(result["translated_text"])
        print("-" * 70)
        print(f"Detected Source:   {result['detected_lang_name']} [{result['detected_lang']}]")
        print(f"Engine Used:       {result['engine_used']}")
        print(f"Latency:           {result['latency_ms']} ms")

        # Audio synthesis if requested
        if args.tts:
            tts = TTSService()
            out_file = Path("outputs") / f"translation_{args.target}.mp3"
            tts.save_speech_file(result["translated_text"], args.target, out_file.name)
            print(f"Speech Audio:      {out_file.resolve()}")

        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nTranslation Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
