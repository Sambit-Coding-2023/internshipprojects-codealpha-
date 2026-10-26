import json
from pathlib import Path
import sys
import time
import warnings

# Configure UTF-8 for Windows terminal output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")

from src.translator import TranslationService



def run_evaluation():
    corpus_file = Path(__file__).parent / "data" / "sample_texts.json"
    if not corpus_file.exists():
        print(f"Error: Benchmark corpus not found at {corpus_file}")
        return

    with open(corpus_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("benchmark_corpus", [])
    service = TranslationService()

    print("=" * 80)
    print("        AI LANGUAGE TRANSLATION ACCURACY & LATENCY BENCHMARK        ")
    print("=" * 80)
    print(f"Evaluating {len(test_cases)} multi-lingual test pairs...")
    print("-" * 80)
    print(f"{'#':<3} | {'LANG PAIR':<10} | {'ENGINE':<20} | {'LATENCY':<8} | {'STATUS':<6} | {'TRANSLATION':<25}")
    print("-" * 80)

    total = len(test_cases)
    passed = 0
    total_latency = 0.0

    for idx, item in enumerate(test_cases, 1):
        src_text = item["source"]
        src_lang = item["source_lang"]
        tgt_lang = item["target_lang"]
        expected = item.get("expected_keywords", [])

        start = time.time()
        try:
            res = service.translate(src_text, source_lang=src_lang, target_lang=tgt_lang)
            output = res["translated_text"]
            latency = res["latency_ms"]
            engine = res["engine_used"]
            total_latency += latency

            # Keyword match check
            output_lower = output.lower()
            keyword_matches = sum(1 for kw in expected if kw.lower() in output_lower)
            is_valid = keyword_matches >= 1 if expected else len(output) > 0

            if is_valid:
                passed += 1
                status = "PASS"
            else:
                status = "WARN"

            pair = f"{src_lang.upper()} -> {tgt_lang.upper()}"
            short_out = (output[:22] + "...") if len(output) > 25 else output
            print(f"{idx:<3} | {pair:<10} | {engine:<20} | {latency:<6.1f}ms | {status:<6} | {short_out}")

        except Exception as e:
            pair = f"{src_lang.upper()} -> {tgt_lang.upper()}"
            print(f"{idx:<3} | {pair:<10} | {'ERROR':<20} | {'N/A':<8} | FAIL   | {str(e)[:25]}")

    print("-" * 80)
    avg_latency = (total_latency / total) if total > 0 else 0
    accuracy = (passed / total) * 100 if total > 0 else 0

    print(f"Overall Accuracy:  {passed}/{total} ({accuracy:.1f}%)")
    print(f"Average Latency:   {avg_latency:.1f} ms")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
