import os
from eth_account import Account

PRIVATE_KEY = os.environ["POLYMARKET_PRIVATE_KEY"]
WALLET_ADDRESS = Account.from_key(PRIVATE_KEY).address

POSITION_SIZE_PCT   = 0.10   # 10% of USDC balance per trade
TOP_TRADER_COUNT    = 20     # traders pulled from leaderboard each cycle
FRESH_TRADE_HOURS   = 6      # only copy trades made within this window
MAX_OPEN_POSITIONS  = 6      # cap on concurrent bets
MIN_PRICE           = 0.05   # skip outcomes priced below 5 cents
MAX_PRICE           = 0.90   # skip outcomes priced above 90 cents
MIN_USDC_TRADE      = 2.0    # minimum order size in USDC

CLOB_HOST = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
DATA_API  = "https://data-api.polymarket.com"

STATE_FILE = "polymarket-bot/state.json"

# Market tags where insider trading is most likely
INSIDER_TAGS = {
    "politics", "elections", "regulation", "government",
    "business", "finance", "legal", "health", "science",
    "crypto", "trump", "congress", "epa", "fda", "sec", "ftc", "doj",
}
