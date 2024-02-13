from schwab_api import Schwab
from dotenv import load_dotenv
import os
import pprint

load_dotenv()

username = os.getenv("SCHWAB_USERNAME")
password = os.getenv("SCHWAB_PASSWORD")
totp_secret = os.getenv("SCHWAB_TOTP")

# Initialize our schwab instance
api = Schwab()

# Login using playwright
print("Logging into Schwab")
logged_in = api.login(
    username=username,
    password=password,
    totp_secret=totp_secret # Get this using itsjafer.com/#/schwab.
)

# Get information about a few tickers
quotes = api.quote_v2(["PFE", "AAPL"])
pprint.pprint(quotes)

# Get information about your accounts holdings
print("Getting account holdings information")
account_info = api.get_account_info_v2()
pprint.pprint(account_info)
account_numbers = list(account_info.keys())
print("The following account numbers were found: " + str(account_numbers))

# Get the lot info for a position in an account
positions = account_info[account_numbers[0]]["positions"]
if positions:
    print(
        f"""Getting lot info for position {positions[0]["security_id"]} in account {account_numbers[0]}""")
    lot_info = api.get_lot_info_v2(
        account_numbers[0], positions[0]["security_id"])
    pprint.pprint(lot_info)

# Get transaction history for an account
print("Getting full transaction history for account " + str(account_numbers[0]))
transaction_history = api.get_transaction_history_v2(account_numbers[0])
pprint.pprint(transaction_history)

print("Placing a dry run trade for PFE stock")
# Place a dry run trade for each account
messages, success = api.trade_v2(
    ticker="PFE", 
    side="Buy", #or Sell
    qty=1, 
    account_id=next(iter(account_info)), # Replace with your account number
    dry_run=True # If dry_run=True, we won't place the order, we'll just verify it.
)

print("The order verification was " + "successful" if success else "unsuccessful")
print("The order verification produced the following messages: ")
pprint.pprint(messages)

orders = api.orders_v2()

pprint.pprint(orders)