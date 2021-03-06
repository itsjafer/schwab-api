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
    totp_secret=totp_secret # Currently working on making this easier for users to get
)

if not logged_in:
    print("Login was not complete; SMS authentication required")
    # If we're not logged in, we need to do SMS confirmation
    success = api.sms_login(
        # Replace this with your SMS code or enter it on the command line
        code=input("Please enter your SMS code: ") 
    )
    
    assert success

# Get information about all accounts holdings
print("Getting account holdings information")
account_info = api.get_account_info()
pprint.pprint(account_info)

print("The following account numbers were found: " + str(account_info.keys()))

print("Placing a dry run trade for AAPL stock")
# Place a dry run trade for each account
messages, success = api.trade(
    ticker="AAPL", 
    side="Buy", #or Sell
    qty=1, 
    account_id=next(iter(account_info)), # Replace with your account number
    dry_run=True # If dry_run=True, we won't place the order, we'll just verify it.
)

print("The order verification was " + "successful" if success else "unsuccessful")
print("The order verification produced the following messages: ")
pprint.pprint(messages)