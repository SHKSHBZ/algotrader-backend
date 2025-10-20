#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import pytz  # optional
    IST = pytz.timezone('Asia/Kolkata')
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / 'audit_logs'
DAILY_DIR = ROOT / 'daily_reports'


def ensure_dirs():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)


def ist_now() -> datetime:
    return datetime.now(IST)


def _atomic_write(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(data)
    os.replace(tmp, path)


def write_scan_audit(payload: Dict[str, Any]) -> Path:
    """Write a per-scan audit JSON file. Returns the path written."""
    ensure_dirs()
    ts = ist_now().strftime('%Y%m%d_%H%M%S')
    path = AUDIT_DIR / f'scan_{ts}.json'
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _merge_daily(existing: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    out = {**existing}
    # Basic counters - use max for scans_today in case of out of order writes
    for k in ['scans_today', 'trades_placed']:
        if k in update:
            out[k] = max(int(existing.get(k, 0)), int(update.get(k, 0)))

    # Portfolio snapshot - last wins
    if 'portfolio_snapshot' in update:
        out['portfolio_snapshot'] = update['portfolio_snapshot']

    # PnL values - last wins
    for k in ['realized_pnl', 'unrealized_pnl']:
        if k in update:
            out[k] = update[k]

    # Arrays - append and de-duplicate by symbol when possible
    def merge_list(key: str, unique_by: Optional[str] = None):
        a = existing.get(key, [])
        b = update.get(key, [])
        merged = a + b
        if unique_by:
            seen = set()
            uniq = []
            for item in merged:
                val = item.get(unique_by) if isinstance(item, dict) else item
                if val not in seen:
                    seen.add(val)
                    uniq.append(item)
            out[key] = uniq
        else:
            out[key] = merged

    for key in ['top_gainers', 'top_losers']:
        merge_list(key, unique_by='symbol')

    for key in ['symbols_with_data_issues', 'notes']:
        merge_list(key)

    # Ensure date_ist is set
    out['date_ist'] = update.get('date_ist', existing.get('date_ist')) or ist_now().date().isoformat()
    return out


def upsert_daily_summary(update: Dict[str, Any]) -> Path:
    """Merge update into today's daily summary and write atomically."""
    ensure_dirs()
    date_str = update.get('date_ist') or ist_now().date().isoformat()
    path = DAILY_DIR / f'{date_str}.json'
    try:
        existing = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    except Exception:
        existing = {}
    merged = _merge_daily(existing, update)
    _atomic_write(path, json.dumps(merged, ensure_ascii=False, indent=2))
    return path
