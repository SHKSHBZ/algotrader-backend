#!/usr/bin/env python3
"""
Prints a concise summary of cached data freshness from data_cache/metadata.json.
Shows per timeframe (15min, 60min, daily): total entries, how many are updated today,
date range, and a short list of stale/missing symbols.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
try:
    import pytz  # Optional; we fallback if not installed
    IST = pytz.timezone('Asia/Kolkata')
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / 'data_cache' / 'metadata.json'

def main():
    today = datetime.now(IST).date().isoformat()
    print(f"Today(IST): {today}")
    if not META.exists():
        print("metadata.json not found. Run download_all_data.py first.")
        return
    try:
        with META.open('r', encoding='utf-8') as f:
            meta = json.load(f)
    except Exception as e:
        print(f"Failed to read metadata.json: {e}")
        return

    def summarize(tf: str):
        items = []
        for k, v in meta.items():
            if not isinstance(k, str) or '_' not in k:
                continue
            sym, key_tf = k.rsplit('_', 1)
            if key_tf != tf:
                continue
            end = str(v.get('end_date', ''))
            end_d = end[:10] if end else ''
            items.append((sym, end_d))

        total = len(items)
        today_count = sum(1 for _, d in items if d == today)
        dates = [d for _, d in items if d]
        min_d = min(dates) if dates else 'NA'
        max_d = max(dates) if dates else 'NA'
        stale = [s for s, d in items if d and d < today]
        missing = [s for s, d in items if not d]

        print(f"\nTF {tf}: total={total} updated_today={today_count} range={min_d} -> {max_d}")
        if stale:
            preview = ', '.join(stale[:10]) + ('...' if len(stale) > 10 else '')
            print(f"  Stale (< today): {preview}")
        if missing:
            preview = ', '.join(missing[:10]) + ('...' if len(missing) > 10 else '')
            print(f"  Missing: {preview}")

    for tf in ['15min', '60min', 'daily']:
        summarize(tf)

if __name__ == '__main__':
    main()
