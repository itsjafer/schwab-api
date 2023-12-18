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

    def trade_v2(self,  
        ticker, 
        side, 
        qty, 
        account_id,
        dry_run=True,
        # The Fields below are experimental fields that should only be changed if you know what you're doing.
        order_type=49,
        duration=48,
        limit_price=0,
        stop_price=0,
        primary_security_type=46,
        valid_return_codes = {0,10}):
        """
            ticker (Str) - The symbol you want to trade,
            side (str) - Either 'Buy' or 'Sell',
            qty (int) - The amount of shares to buy/sell,
            account_id (int) - The account ID to place the trade on. If the ID is XXXX-XXXX, 
                         we're looking for just XXXXXXXX.
            order_type (int) - The order type. This is a Schwab-specific number, and there exists types 
                        beyond 49 (Market) and 50 (Limit). This parameter allows setting specific types
                        for those willing to trial-and-error.
            duration (int) - The duration type for the order. For now, all that's been 
                        tested is value 48 mapping to Day-only orders.
            limit_price (number) - The limit price to set with the order, if necessary.
            stop_price (number) -  The stop price to set with the order, if necessary.
            primary_security_type (int) - The type of the security being traded. 

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

        self.update_token()
        
        data = {
            "UserContext": {
                "AccountId":str(account_id),
                "AccountColor":0
            },
            "OrderStrategy": {
                # Unclear what the security types map to.
                "PrimarySecurityType":primary_security_type,
                "CostBasisRequest": {
                    "costBasisMethod":"FIFO",
                    "defaultCostBasisMethod":"FIFO"
                },
                "OrderType":str(order_type),
                "LimitPrice":str(limit_price),
                "StopPrice":str(stop_price),
                "Duration":str(duration),
                "AllNoneIn":False,
                "DoNotReduceIn":False,
                "OrderStrategyType":1,
                "OrderLegs":[
                    {
                        "Quantity":str(qty),
                        "LeavesQuantity":str(qty),
                        "Instrument":{"Symbol":ticker},
                        "SecurityType":primary_security_type,
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
        if response["orderStrategy"]["orderReturnCode"] not in valid_return_codes:
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

    def quote_v2(self, tickers):
        """
        quote_v2 takes a list of Tickers, and returns Quote information through the Schwab API.
        """
        self.update_token()
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

    def orders_v2(self, account_id=None):
        """
        orders_v2 returns a list of orders for a Schwab Account. It is unclear to me how to filter by specific account.

        Currently, the query parameters are hard coded to return ALL orders, but this can be easily adjusted.
        """

        self.update_token()
        self.headers['schwab-resource-version'] = '2.0'
        if account_id:
            self.headers["schwab-client-account"] = account_id
        r = self.session.get(urls.orders_v2(), headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)
        return response["Orders"]
    
    def get_account_info_v2(self):
        account_info = dict()
        self.update_token()
        r = self.session.get(urls.positions_v2(), headers=self.headers)
        response = json.loads(r.text)
        for account in response['accounts']:
            positions = list()
            for security_group in account["groupedPositions"]:
                if security_group["groupName"] == "Cash":
                    continue
                for position in security_group["positions"]:
                    positions.append(
                        Position(
                            position["symbolDetail"]["symbol"],
                            position["symbolDetail"]["description"],
                            int(position["quantity"]),
                            float(position["costDetail"]["costBasisDetail"]["costBasis"]),
                            float(position["priceDetail"]["marketValue"])
                        )._as_dict()
                    )
            account_info[int(account["accountId"])] = Account(
                account["accountId"],
                positions,
                account["totals"]["marketValue"],
                account["totals"]["cashInvestments"],
                account["totals"]["accountValue"],
                account["totals"].get("costBasis", 0),
            )._as_dict()

        return account_info
    
    def update_token(self):
        self.session.cookies.pop('ADRUM_BT1', None)
        self.session.cookies.pop('ADRUM_BTa', None)
        r = self.session.get("https://client.schwab.com/api/auth/authorize/scope/api")
        token = json.loads(r.text)['token']
        self.headers['authorization'] = f"Bearer {token}"