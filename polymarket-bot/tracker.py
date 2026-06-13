import json
import os
from datetime import datetime
from config import STATE_FILE

_EMPTY = {"copied": [], "last_run": None}

def _load() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return dict(_EMPTY)

def _save(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def _key(trader: str, market: str, outcome: str) -> str:
    return f"{trader.lower()}:{market.lower()}:{outcome.upper()}"

def already_copied(trader: str, market: str, outcome: str) -> bool:
    state = _load()
    k = _key(trader, market, outcome)
    return any(c["key"] == k for c in state["copied"])

def mark_copied(trader: str, market: str, outcome: str, order_id: str = None):
    state = _load()
    state["copied"].append({
        "key": _key(trader, market, outcome),
        "trader": trader,
        "market": market,
        "outcome": outcome,
        "order_id": order_id,
        "ts": datetime.utcnow().isoformat(),
    })
    state["last_run"] = datetime.utcnow().isoformat()
    _save(state)

def touch_last_run():
    state = _load()
    state["last_run"] = datetime.utcnow().isoformat()
    _save(state)
