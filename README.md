# Schwab API

![Screenshot](screenshot.png)

**This is not an official API or even a stable recreation of a Charles Schwab API. Functionality may change with any updates made by Schwab.**

This package enables buying and selling securities programmatically on Charles Schwab. Currently, we use a headless browser to automate logging in in order to get authorization cookies. All other functionality is done through web requests made to Schwab's own API.


## Live Demo

I am currently using this package to place trades on Schwab using my website [here](https://itsjafer.com/#/reversesplit)

## Contribution

I would absolutely love contributions; as someone new to open source, I'd appreciate help in setting up a reliable system for PRs as well :)

## Getting Started

### Installing

Install using pypi and then download and install the playwright binaries:

```
pip install schwab-api
python -m playwright install
```

### Quickstart

Here's some code that logs in, gets all account holdings, and makes a stock purchase:
```
from schwab_api import Schwab

# Initialize our schwab instance
# We can only have one instance running at a time

# If you know your TOTP secret, pass that into the `totp` parameter in get_instance
# How to get TOTP: https://www.reddit.com/r/personalfinance/comments/hvvuwl/using_google_auth_or_your_totp_app_of_choice_for/ 
# Initialize our schwab instance
api = Schwab(
    username="username",
    password="password",
    totp="totp" # if totp is not given, you'll be asked to enter a code you receive as SMS
)

# Login using playwright to get authorization cookies
api.login(screenshot=False)

# Get information about all accounts holdings
account_info = api.get_account_info()
print(account_info)

# Place a dry run trade for a given account number
messages, success = api.trade(
    ticker="AAPL", 
    side="Buy", #or Sell
    qty=1, 
    account_id=99999999, # Replace with your acount number
    dry_run=True # If dry_run=True, we won't place the order, we'll just verify it.
)
```

## Documentation

There is currently no documentation. If there is traction or demand, I will slowly add this in.

## Features

* Buying and Selling tickers
* Multiple individual account support
* MFA and TOTP authentication
* Account and Position Information
* Headless playwright implementation

## TODO

* Currently, we use a headless browser to login to Schwab; in the future, we want to do this purely with requests.

