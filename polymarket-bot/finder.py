import logging
import requests
from config import DATA_API, TOP_TRADER_COUNT

logger = logging.getLogger(__name__)

def get_top_traders() -> list[str]:
    """Return proxy wallet addresses of top monthly P&L traders from the leaderboard."""
    try:
        resp = requests.get(
            f"{DATA_API}/leaderboard",
            params={"window": "monthly", "limit": TOP_TRADER_COUNT},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        traders = []
        for entry in data:
            # Field name varies across API versions
            addr = (
                entry.get("address")
                or entry.get("proxyWallet")
                or entry.get("proxy_wallet")
            )
            if addr:
                traders.append(addr)

        logger.info(f"Leaderboard: {len(traders)} traders fetched")
        return traders
    except Exception as e:
        logger.error(f"Leaderboard fetch failed: {e}")
        return []
