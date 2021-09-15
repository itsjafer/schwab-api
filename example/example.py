from schwab_api import Schwab
from dotenv import load_dotenv
import os
import pyotp

load_dotenv()
def main():

    username = os.getenv("SCHWAB_USERNAME")
    password = os.getenv("SCHWAB_PASSWORD")
    totp = os.getenv("SCHWAB_TOTP")

    # Initialize our schwab instance
    api = Schwab(
        username=username,
        password=password,
        totp=totp,
        headless=True
    )

    # Login using playwright
    api.login(screenshot=True)
    # Get information about all accounts holdings
    account_info = api.get_account_info()
    print(account_info)

    # Place a dry run trade for each account
    messages, success = api.trade(
        ticker="AAPL", 
        side="Buy", #or Sell
        qty=1, 
        account_id=99999999, # Replace with your acount number
        dry_run=True # If dry_run=True, we won't place the order, we'll just verify it.
    )

    print(success)
    print(messages)

main()