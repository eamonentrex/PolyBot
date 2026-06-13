import logging
import requests
from datetime import datetime, timezone, timedelta
from config import DATA_API, GAMMA_API, FRESH_TRADE_HOURS, INSIDER_TAGS

logger = logging.getLogger(__name__)

# In-memory cache so we don't hit Gamma API repeatedly for the same market
_tag_cache: dict[str, bool] = {}

def _market_has_insider_tag(condition_id: str) -> bool:
    if condition_id in _tag_cache:
        return _tag_cache[condition_id]

    try:
        resp = requests.get(
            f"{GAMMA_API}/markets",
            params={"condition_ids": condition_id},
            timeout=10,
        )
        resp.raise_for_status()
        markets = resp.json()
        if not markets:
            _tag_cache[condition_id] = False
            return False

        market = markets[0] if isinstance(markets, list) else markets
        tags: set[str] = set()

        for raw in market.get("tags") or market.get("categories") or []:
            if isinstance(raw, str):
                tags.add(raw.lower())
            elif isinstance(raw, dict):
                label = raw.get("label") or raw.get("slug") or ""
                tags.add(label.lower())

        result = bool(tags & INSIDER_TAGS)
        _tag_cache[condition_id] = result
        return result
    except Exception as e:
        logger.warning(f"Tag check failed for {condition_id}: {e}")
        _tag_cache[condition_id] = False
        return False


def get_recent_trades(trader_addr: str) -> list[dict]:
    """
    Fetch fresh BUY trades for a trader in insider-likely markets.
    Returns list of dicts: {trader, market, outcome, price, usdc_size, timestamp}
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESH_TRADE_HOURS)

    try:
        resp = requests.get(
            f"{DATA_API}/activity",
            params={"user": trader_addr, "limit": 50},
            timeout=15,
        )
        resp.raise_for_status()
        activity = resp.json()
    except Exception as e:
        logger.error(f"Activity fetch failed for {trader_addr[:10]}...: {e}")
        return []

    results = []
    for item in activity:
        ts_raw = item.get("timestamp") or item.get("createdAt") or item.get("ts")
        if not ts_raw:
            continue

        try:
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            continue

        if ts < cutoff:
            continue

        # Skip sells
        side = (item.get("side") or item.get("type") or "BUY").upper()
        if side == "SELL":
            continue

        market = (
            item.get("market")
            or item.get("conditionId")
            or item.get("condition_id")
        )
        outcome = item.get("outcome") or item.get("outcomeIndex")
        price = item.get("price") or item.get("outcomePrice")
        usdc_size = item.get("size") or item.get("usdcSize") or item.get("amount") or 0

        if not all([market, outcome is not None, price]):
            continue

        # Normalize outcome to YES/NO
        if isinstance(outcome, int):
            outcome = "YES" if outcome == 0 else "NO"
        outcome = str(outcome).strip().upper()
        if outcome not in ("YES", "NO"):
            continue

        if not _market_has_insider_tag(market):
            continue

        results.append({
            "trader": trader_addr,
            "market": market,
            "outcome": outcome,
            "price": float(price),
            "usdc_size": float(usdc_size),
            "timestamp": ts.isoformat(),
        })

    return results
