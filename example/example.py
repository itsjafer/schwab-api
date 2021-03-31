from schwab import Schwab
from dotenv import load_dotenv
import os

load_dotenv()
def main():

    username = os.getenv("SCHWAB_USERNAME")
    password = os.getenv("SCHWAB_PASSWORD")
    user_agent = os.getenv("SCHWAB_USER_AGENT")

    # Initialize our schwab instance
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

main()