import logging
import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.constants import POLYGON
from config import (
    PRIVATE_KEY, WALLET_ADDRESS, CLOB_HOST, DATA_API,
    POSITION_SIZE_PCT, MIN_PRICE, MAX_PRICE, MIN_USDC_TRADE,
)

logger = logging.getLogger(__name__)

_client: ClobClient | None = None


def get_client() -> ClobClient:
    global _client
    if _client is None:
        _client = ClobClient(host=CLOB_HOST, key=PRIVATE_KEY, chain_id=POLYGON)
        creds = _client.create_or_derive_api_creds()
        _client.set_api_creds(creds)
        logger.info(f"CLOB client ready — wallet {WALLET_ADDRESS[:10]}...")
    return _client


def get_usdc_balance() -> float:
    try:
        bal = get_client().get_balance()
        return float(str(bal))
    except Exception as e:
        logger.error(f"Balance fetch failed: {e}")
        return 0.0


def get_open_position_count() -> int:
    try:
        resp = requests.get(
            f"{DATA_API}/positions",
            params={"user": WALLET_ADDRESS, "sizeThreshold": "0.1"},
            timeout=10,
        )
        resp.raise_for_status()
        return len(resp.json())
    except Exception as e:
        logger.warning(f"Position count failed: {e}")
        return 0


def _get_token_id(condition_id: str, outcome: str) -> str | None:
    try:
        market = get_client().get_market(condition_id)
        tokens = market.get("tokens", []) if isinstance(market, dict) else market.tokens
        for token in tokens:
            if isinstance(token, dict):
                t_outcome = token.get("outcome", "")
                t_id = token.get("token_id", "")
            else:
                t_outcome = token.outcome
                t_id = token.token_id
            if t_outcome.upper() == outcome.upper():
                return t_id
    except Exception as e:
        logger.error(f"Token lookup failed for {condition_id}/{outcome}: {e}")
    return None


def _get_best_ask(token_id: str) -> float | None:
    try:
        book = get_client().get_orderbook(token_id)
        asks = book.get("asks", []) if isinstance(book, dict) else book.asks
        if asks:
            first = asks[0]
            price = first.get("price") if isinstance(first, dict) else first.price
            return float(price)
    except Exception as e:
        logger.warning(f"Orderbook fetch failed for {token_id[:12]}...: {e}")
    return None


def place_copy_trade(market: str, outcome: str) -> str | None:
    """
    Buy `outcome` (YES or NO) on `market` using 10% of USDC balance.
    Returns order ID on success, None on failure.
    """
    token_id = _get_token_id(market, outcome)
    if not token_id:
        return None

    current_price = _get_best_ask(token_id)
    if current_price is None:
        return None

    if not (MIN_PRICE <= current_price <= MAX_PRICE):
        logger.info(f"Price {current_price:.3f} outside range — skipping {market[:12]}...")
        return None

    balance = get_usdc_balance()
    usdc_amount = round(balance * POSITION_SIZE_PCT, 2)

    if usdc_amount < MIN_USDC_TRADE:
        logger.warning(f"Trade size ${usdc_amount:.2f} below minimum ${MIN_USDC_TRADE}")
        return None

    logger.info(f"Buying {outcome} @ {current_price:.3f} for ${usdc_amount:.2f} on {market[:16]}...")

    try:
        signed = get_client().create_market_order(
            MarketOrderArgs(token_id=token_id, amount=usdc_amount)
        )
        resp = get_client().post_order(signed, OrderType.FOK)

        if isinstance(resp, dict):
            order_id = resp.get("orderID") or resp.get("order_id") or resp.get("id")
        else:
            order_id = getattr(resp, "orderID", None) or getattr(resp, "order_id", None)

        if order_id:
            logger.info(f"Order filled: {order_id}")
            return str(order_id)

        logger.warning(f"Order posted but no ID returned: {resp}")
        return "posted"
    except Exception as e:
        logger.error(f"Order failed: {e}")
        return None
