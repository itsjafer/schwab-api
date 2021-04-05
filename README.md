# Schwab API

![Screenshot](screenshot.png)

**This is not an official API or even a stable recreation of a Charles Schwab API. Functionality may change with any updates made by Schwab.**

This package enables buying and selling securities programmatically on Charles Schwab using Playwright. Essentially, this package uses headless Chromium to automate the clicks and inputs; it does NOT use web requests (though I'd love to change the code to do so).

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

Here's some code that logs in and makes a stock purchase:
```
from schwab_api import Schwab

# Initialize our schwab instance
# We can only have one instance running at a time
api = Schwab.get_instance(
    username=username,
    password=password,
    user_agent=user_agent
)

# Login
# First-time setup: you will need to enter an SMS confirmation code as input
api.login()

# Make a trade
api.trade(
    ticker="ticker", 
    side="Buy", ## or "Sell"
    qty=1
)
```

## Documentation

There is currently no documentation. If there is traction or demand, I will slowly add this in.

## Features

* Buying and Selling tickers
* Multiple individual account support
* Persistent authentication (after an initial MFA setup)
* Headless playwright implementation

## Todo

* Other functions beyond just trading
  * Account information
  * Position information
  * More advanced trading functions
* Get this setup on a VM or a cloud function
* Randomize and humanize every click and input interaction

