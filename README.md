# schwab-python

**This is not an official API or even a stable recreation of a Charles Schwab API. Functionality may change with any updates made by Schwab.**

This package enables buying and selling securities programmatically on Charles Schwab using Playwright. Essentially, this package uses headless Chromium to automate the clicks and inputs; it does NOT use web requests (though I'd love to change the code to do so).

## Getting Started

### Installing

I plan to publish this to pypi soon. Until then, you're going to want to clone the repo and install like so:

```
git clone https://github.com/itsjafer/schwab-python.git
cd schwab-python
pip install .
python -m playwright install
```

### Quickstart

Here's some code that logs in and makes a stock purchase:
```
from schwab import Schwab

# Initialize our schwab instance
# We can only have one instance running at a time
api = Schwab.get_instance(
    username=username,
    password=password,
    user_agent=user_agent
)

# Login
# First-time setup: you will need to enter an SMS confirmation code as input
api.login(screenshot=True)

# Make a trade
api.trade(
    ticker="ticker", 
    side="Buy" ## or "Sell", 
    qty=1,
    screenshot=False # for debugging turn this on
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

* Export an actual function for modular use
* Get this setup on a VM or a cloud function
* Randomize and humanize every click and input interaction

