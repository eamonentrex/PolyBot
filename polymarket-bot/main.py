"""
Polymarket Copy Bot
Monitors the top monthly P&L traders and mirrors their bets in insider-likely markets.
Runs every 15 minutes via GitHub Actions.
"""

import logging
import sys
from config import MAX_OPEN_POSITIONS, MIN_PRICE, MAX_PRICE
from finder import get_top_traders
from scraper import get_recent_trades
from trader import place_copy_trade, get_open_position_count
from tracker import already_copied, mark_copied, touch_last_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run_cycle():
    logger.info("=== Polymarket copy cycle starting ===")

    open_positions = get_open_position_count()
    logger.info(f"Open positions: {open_positions}/{MAX_OPEN_POSITIONS}")

    if open_positions >= MAX_OPEN_POSITIONS:
        logger.info("Position limit reached — waiting for markets to resolve")
        touch_last_run()
        return

    traders = get_top_traders()
    if not traders:
        logger.warning("No traders returned from leaderboard — aborting cycle")
        touch_last_run()
        return

    slots = MAX_OPEN_POSITIONS - open_positions
    placed = 0

    for trader in traders:
        if placed >= slots:
            break

        trades = get_recent_trades(trader)
        for trade in trades:
            if placed >= slots:
                break

            market  = trade["market"]
            outcome = trade["outcome"]
            price   = trade["price"]

            if not (MIN_PRICE <= price <= MAX_PRICE):
                continue

            if already_copied(trader, market, outcome):
                continue

            order_id = place_copy_trade(market, outcome)
            mark_copied(trader, market, outcome, order_id=order_id)

            if order_id:
                placed += 1
                logger.info(
                    f"Copied | trader={trader[:10]}... | market={market[:14]}... "
                    f"| {outcome} @ {price:.3f}"
                )

    logger.info(f"=== Cycle complete — {placed} trade(s) placed ===")


if __name__ == "__main__":
    run_cycle()
