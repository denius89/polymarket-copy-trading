"""Retired 16-Oct diagnostic entrypoint; import-safe, never overwrites history.

Original source is preserved alongside this file as .2026-10-16.py.txt.
Use the versioned qualification runner described below. This guard intentionally
rejects old commands so a known unsafe historical implementation cannot run silently.
"""
import sys

def main():
    print("Retired diagnostic: historical results are read-only. Run the corrected version with a NEW output directory:\n"
          "PYTHONPATH=/tmp/trader-score-python-deps python3 research/trader-score-reference-2026-10-18/analyze_recorded.py --output-dir NEW_OUTPUT_DIRECTORY", file=sys.stderr)
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
