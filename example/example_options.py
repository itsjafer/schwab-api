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
# If you would like to view the output, prefer saving it as a text file.

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

#get quotes for options.
OptionChain = api.get_options_chains_v2('$RUT',[Dates[0],Dates[1]]) #try also with parameter greeks = True 

#the json output is deeply nested so here is how you can work with it
#normalizing the data into a pandas DataFrame
df1 = pd.json_normalize(OptionChain,['Expirations','Chains','Legs'],[['Expirations','ExpirationGroup']])
#normalizing Expirations.ExpirationGroup
df2 = pd.json_normalize(df1['Expirations.ExpirationGroup'])
#dropping the column Expirations.ExpirationGroup in df1 and concatenating the two dataframes (side by side)
df1.drop('Expirations.ExpirationGroup',axis=1, inplace=True)
df = pd.concat([df1,df2],axis=1)
#converting strings to numbers when relevant. Keeping strings is conversion is not possible.
df = df.apply(lambda col: pd.to_numeric(col, errors='coerce')).fillna(df)

#let's isolate options with closest expiration date:
closest_expiration_options = df[(df.DaysUntil==df.DaysUntil.min())]

#let's find the call and put options with closest strike price to current price:
#first let's grab the current price. No need to use api.quote_v2(), it's already in chains
current_price = float(chains['UnderlyingData']['Last'])
#finding the index of the closest strike prices
ATM_call_index = abs(closest_expiration_options[closest_expiration_options.OptionType=="C"].Strk - current_price).idxmin()
ATM_put_index = abs(closest_expiration_options[closest_expiration_options.OptionType=="P"].Strk - current_price).idxmin()
#grabbing the rows at those indexes 
ATM_call_option = closest_expiration_options.iloc[ATM_call_index]
ATM_put_option = closest_expiration_options.iloc[ATM_put_index]
print(f"The At The Money options with the closest expiration have symbols:  and {ATM_put_option.Sym}")
print(f"{ATM_call_option.Sym}         Ask: {ATM_call_option.Ask}      Bid: {ATM_call_option.Bid}")
print(f"{ATM_put_option.Sym}         Ask: {ATM_put_option.Ask}      Bid: {ATM_put_option.Bid}")

#now let's place an at the money straddle for the closest expiration date
#preparing the parameters
symbols = [ATM_call_option.Sym,ATM_call_option.Sym]
instructions = ["BTO","BTO"] #Buy To Open. To close the position, it would be STC (Sell To Close)
quantities = [1,1]
#note that the elements are paired. So the first symbol of the list will be associated with the first element of instructions and quantities.
account_info = api.get_account_info_v2()
account_id = next(iter(account_info))
order_type = 202 #net debit. 201 for net credit. You probably should avoid 49 market with options...
# let's set the limit price at the median between bid and ask.
limit_price = (ATM_call_option.Ask + ATM_call_option.Bid + ATM_put_option.Ask + ATM_put_option.Bid) / 2
#let's place the trade:
messages, success = api.option_trade_v2(
    strategy=226, 
    symbols = symbols, 
    instructions=instructions, 
    quantities=quantities, 
    account_id=account_id, 
    order_type = order_type,
    dry_run=True,
    limit_price = limit_price
)
print("The order verification was " + "successful" if success else "unsuccessful")
print("The order verification produced the following messages: ")
pprint.pprint(messages)

#Happy coding!!
