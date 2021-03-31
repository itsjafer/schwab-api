# schwab-trader

*This is a work in progress*

This is a basic python script that uses playwright to login to Charles Schwab and buy or sell a given ticker.

## Setup

You must create a `.env` file or set the following variables:

```
SCHWAB_USERNAME
SCHWAB_PASSWORD
SCHWAB_USER_DATA_DIR
SCHWAB_NUM_ACCOUNTS
SCHWAB_USER_AGENT
```

## Features

* Buying and Selling tickers
* Multiple individual account support
* Persistent authentication (after an initial MFA setup)
* Headless playwright implementation

## Todo

* Get this setup on a VM or a cloud function
* Randomize and humanize every click and input interaction
* Set up the repo as a package
* Replace playwright with actual reverse engineered API calls

