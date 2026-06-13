import logging
import requests
from config import DATA_API, TOP_TRADER_COUNT

logger = logging.getLogger(__name__)

# Try different param combinations since Polymarket's leaderboard API isn't fully documented
_LEADERBOARD_PARAMS = [
    {"limit": TOP_TRADER_COUNT},
    {"limit": TOP_TRADER_COUNT, "window": "all"},
    {"limit": TOP_TRADER_COUNT, "interval": "monthly"},
    {"limit": TOP_TRADER_COUNT, "window": "1m"},
    {"limit": TOP_TRADER_COUNT, "timeframe": "monthly"},
]

def get_top_traders() -> list[str]:
    """Return proxy wallet addresses of top traders from the Polymarket leaderboard."""
    for params in _LEADERBOARD_PARAMS:
        try:
            resp = requests.get(
                f"{DATA_API}/leaderboard",
                params=params,
                timeout=15,
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            if not data:
                continue

            traders = []
            for entry in data:
                addr = (
                    entry.get("address")
                    or entry.get("proxyWallet")
                    or entry.get("proxy_wallet")
                )
                if addr:
                    traders.append(addr)

            if traders:
                logger.info(f"Leaderboard: {len(traders)} traders (params={params})")
                return traders
        except Exception as e:
            logger.warning(f"Leaderboard attempt failed (params={params}): {e}")
            continue

    logger.error("All leaderboard endpoint attempts failed — check Polymarket API docs for correct URL")
    return []
