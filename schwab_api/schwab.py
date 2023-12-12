import json
import urllib.parse

from . import urls
from .account_information import Position, Account
from .authentication import SessionManager

class Schwab(SessionManager):
    def __init__(self, **kwargs):
        """
            The Schwab class. Used to interact with schwab.

        """
        self.headless = kwargs.get("headless", True)
        self.browserType = kwargs.get("browserType", "firefox")
        super(Schwab, self).__init__()
   
    def get_account_info(self):
        """
            Returns a dictionary of Account objects where the key is the account number
        """
        
        account_info = dict()
        r = self.session.get(urls.positions_data())
        response = json.loads(r.text)
        for account in response['Accounts']:
            positions = list()
            for security_group in account["SecurityGroupings"]:
                for position in security_group["Positions"]:
                    positions.append(
                        Position(
                            position["DefaultSymbol"],
                            position["Description"],
                            int(position["Quantity"]),
                            float(position["Cost"]),
                            float(position["MarketValue"])
                        )._as_dict()
                    )

                    if not "ChildOptionPositions" in position:
                        continue

                    # Add call positions if they exist 
                    for child_position in position["ChildOptionPositions"]:
                        positions.append(
                            Position(
                                child_position["DefaultSymbol"],
                                child_position["Description"],
                                int(child_position["Quantity"]),
                                float(child_position["Cost"]),
                                float(child_position["MarketValue"])
                            )._as_dict()
                        )
            account_info[int(account["AccountId"])] = Account(
                account["AccountId"],
                positions,
                account["Totals"]["MarketValue"],
                account["Totals"]["CashInvestments"],
                account["Totals"]["AccountValue"],
                account["Totals"]["Cost"],
            )._as_dict()

        return account_info


    def trade_v2(self,  ticker, side, qty, account_id, dry_run=True):
        """
            ticker (Str) - The symbol you want to trade,
            side (str) - Either 'Buy' or 'Sell',
            qty (int) - The amount of shares to buy/sell,
            account_id (int) - The account ID to place the trade on. If the ID is XXXX-XXXX, 
                         we're looking for just XXXXXXXX.

            Note: this function calls the new Schwab API, which is flakier and seems to have stricter authentication requirements.
            For now, only use this function if the regular trade function doesn't work for your use case.

            Returns messages (list of strings), is_success (boolean)
        """

        if side == "Buy":
            buySellCode = "49"
        elif side == "Sell":
            buySellCode = "50"
        else:
            raise Exception("side must be either Buy or Sell")

        data = {
            "UserContext": {
                "AccountId":str(account_id),
                "AccountColor":0
            },
            "OrderStrategy": {
                # Unclear what the security types map to.
                "PrimarySecurityType":46,
                "CostBasisRequest": {
                    "costBasisMethod":"FIFO",
                    "defaultCostBasisMethod":"FIFO"
                },
                "OrderType":"49",
                "LimitPrice":"0",
                "StopPrice":"0",
                "Duration":"48",
                "AllNoneIn":False,
                "DoNotReduceIn":False,
                "OrderStrategyType":1,
                "OrderLegs":[
                    {
                        "Quantity":str(qty),
                        "LeavesQuantity":str(qty),
                        "Instrument":{"Symbol":ticker},
                        "SecurityType":46,
                        "Instruction":buySellCode
                    }
                    ]},
            # OrderProcessingControl seems to map to verification vs actually placing an order.
            "OrderProcessingControl":1
        }

        # Adding this header seems to be necessary.
        self.headers['schwab-resource-version'] = '1.0'

        r = self.session.post(urls.order_verification_v2(), json=data, headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)

        orderId = response['orderStrategy']['orderId']
        messages = list()
        for message in response["orderStrategy"]["orderMessages"]:
            messages.append(message["message"])

        # TODO: This needs to be fleshed out and clarified.
        if response["orderStrategy"]["orderReturnCode"] not in {0, 10}:
            print(r.text)
            return messages, False

        if dry_run:
            return messages, True

        # Make the same POST request, but for real this time.
        data["UserContext"]["CustomerId"] = 0
        data["OrderStrategy"]["OrderId"] = int(orderId)
        data["OrderProcessingControl"] = 2
        r = self.session.post(urls.order_verification_v2(), json=data, headers=self.headers)

        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)

        messages = list()
        if "orderMessages" in response["orderStrategy"] and response["orderStrategy"]["orderMessages"] is not None:
            for message in response["orderStrategy"]["orderMessages"]:
                messages.append(message["message"])

        if response["orderStrategy"]["orderReturnCode"] == 0:
            return messages, True
        
        return messages, False

    def trade(self, ticker, side, qty, account_id, dry_run=True):
        """
            ticker (Str) - The symbol you want to trade,
            side (str) - Either 'Buy' or 'Sell',
            qty (int) - The amount of shares to buy/sell,
            account_id (int) - The account ID to place the trade on. If the ID is XXXX-XXXX, 
                         we're looking for just XXXXXXXX.

            Returns messages (list of strings), is_success (boolean)
        """

        if side == "Buy":
            buySellCode = 1
        elif side == "Sell":
            buySellCode = 2
        else:
            raise Exception("side must be either Buy or Sell")

        data = {
            "IsMinQty":False,
            "CustomerId":str(account_id),
            "BuySellCode":buySellCode,
            "Quantity":str(qty),
            "IsReinvestDividends":False,
            "SecurityId":ticker,
            "TimeInForce":"1", # Day Only
            "OrderType":1, # Market Order
            "CblMethod":"FIFO",
            "CblDefault":"FIFO",
            "CostBasis":"FIFO",
            }

        r = self.session.post(urls.order_verification(), data)

        if r.status_code != 200:
            return [r.text], False
        
        response = json.loads(r.text)

        messages = list()
        for message in response["Messages"]:
            messages.append(message["Message"])

        if dry_run:
            return messages, True

        data = {
            "AccountId": str(account_id),
            "ActionType": side,
            "ActionTypeText": side,
            "BuyAction": side == "Buy",
            "CostBasis": "FIFO",
            "CostBasisMethod": "FIFO",
            "IsMarketHours": True,
            "ItemIssueId": int(response['IssueId']),
            "NetAmount": response['NetAmount'],
            "OrderId": int(response["Id"]),
            "OrderType": "Market",
            "Principal": response['QuoteAmount'],
            "Quantity": str(qty),
            "ShortDescription": urllib.parse.quote_plus(response['IssueShortDescription']),
            "Symbol": response["IssueSymbol"],
            "Timing": "Day Only"
        }

        r = self.session.post(urls.order_confirmation(), data)

        if r.status_code != 200:
            messages.append(r.text)
            return messages, False

        response = json.loads(r.text)
        if response["ReturnCode"] == 0:
            return messages, True

        return messages, False

    def quote(self, tickers):
        data = {
            "Symbols":tickers,
            "IsIra":False,
            "AccountRegType":"S3"
        }

        # Adding this header seems to be necessary.
        self.headers['schwab-resource-version'] = '1.0'

        r = self.session.post(urls.ticker_quotes_v2(), json=data, headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)
        return response["quotes"]