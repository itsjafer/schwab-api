from schwab_api import Schwab, options
from dotenv import load_dotenv
import os
import pandas as pd

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

# Get information about a RUT option series
option_series_json = api.get_option_series_v2("$RUT")
# The result is quite long.
# If you would like to view the output, prefer saving it as a text file than printing it

# Post process some option_series information
RUT_option_series = options.OptionSeries(option_series_json)
Dates = RUT_option_series.get_expiration_dates()
from datetime import datetime
print(f"3rd date of option series: {Dates[2].strftime('%m/%d/%Y')}")
Roots = RUT_option_series.get_roots(Dates[2])
print(f"Root symbols available for that date: {Roots}")
print(f"Selecting Root: {Roots[0]}")
Strikes = RUT_option_series.get_strikes(Dates[2])
#note that strikes can be for different root symbols. They are organized by root index.
#Strikes[0] will be a list of strike prices for Roots[0]
#Strikes[1] will be a list of strike prices for Roots[1] etc.
print(f"Root symbols available for that date: {Roots}")
print(f"Selecting Strike: {Strikes[0][5]} of Root {Roots[0]}")
OptionTickers = options.generate_option_symbol(Roots[0],Dates[2],Strikes[0][5],"Call")
print(f"option ticker for $RUT with expiration {Dates[2].strftime('%m/%d/%Y')} at strike price {Strikes[0][5]}: {OptionTickers}")

OptionChain = api.get_options_chains_v2('$RUT',[Dates[0],Dates[1]], greeks=True)

#normalizing the data into a pandas DataFrame
df1 = pd.json_normalize(OptionChain,['Expirations','Chains','Legs'],[['Expirations','ExpirationGroup']])
df2 = pd.json_normalize(df1['Expirations.ExpirationGroup'])
df1.drop('Expirations.ExpirationGroup',axis=1, inplace=True)
df = pd.concat([df1,df2],axis=1)
#convert strings to numbers when relevant.
df = df.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(df)

#Happy coding!!
