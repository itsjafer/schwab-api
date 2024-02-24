from schwab_api import Schwab
from dotenv import load_dotenv
import os
import pandas as pd
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

#get quotes for options.
OptionChain = api.get_options_chains_v2('$RUT') #try also with parameter greeks = True 

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
current_price = float(OptionChain['UnderlyingData']['Last'])
#finding the index of the closest strike prices
ATM_call_index = abs(closest_expiration_options[closest_expiration_options.OptionType=="C"].Strk - current_price).idxmin()
ATM_put_index = abs(closest_expiration_options[closest_expiration_options.OptionType=="P"].Strk - current_price).idxmin()
#grabbing the rows at those indexes 
ATM_call_option = closest_expiration_options.iloc[ATM_call_index]
ATM_put_option = closest_expiration_options.iloc[ATM_put_index]
print(f"Call and Put ATM options (At The Money) with the closest expiration:")
print(f"Call: {ATM_call_option.Sym}         Ask: {ATM_call_option.Ask}      Bid: {ATM_call_option.Bid}")
print(f"Put:  {ATM_put_option.Sym}         Ask: {ATM_put_option.Ask}      Bid: {ATM_put_option.Bid}")

#now let's place an at the money straddle for the closest expiration date
#preparing the parameters
#setting the straddle strategy code:
strategy = 226 # for more codes, look at the comment section of option_trade_v2().
symbols = [ATM_call_option.Sym,ATM_put_option.Sym]
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
    strategy=strategy, 
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