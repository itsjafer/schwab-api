import json
import urllib.parse
import requests

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
        # In order for this to return info for all accounts, the web interface excludes the
        # AcctInfo cookie and sets the CustAccessInfo cookie to a value like:
        # '<something>|<some_acct_num>|AllAccts'
        # instead of:
        # '<something>|<some_acct_num>|'
        # There can be multiple cookies with the same name but having different attributes,
        # i.e. domains '' and '.schwab.com', so we need to be careful when deleting or modifying
        # cookies with a certain name
        requests.cookies.remove_cookie_by_name(self.session.cookies, 'AcctInfo')
        for cookie in self.session.cookies:
            if cookie.name == 'CustAccessInfo':
                if cookie.value.endswith('|'):
                    cookie.value += 'AllAccts'
                    self.session.cookies.set_cookie(cookie)
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
                            float(position["Quantity"]),
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
                                float(child_position["Quantity"]),
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
        valid_return_codes = {0,10},
        affirm_order=False,
        ):
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
            valid_return_codes (set) - Schwab returns an orderReturnCode in the response to both
                        the verification and execution requests, and it appears to be the
                        "severity" for the highest severity message.
                        Verification response messages with severity 10 include:
                            - The market is now closed. This order will be placed for the next
                              trading day
                            - You are purchasing an ETF...please read the prospectus
                            - It is your responsibility to choose the cost basis method
                              appropriate to your tax situation
                            - Quote at the time of order verification: $xx.xx
                        Verification response messages with severity 20 include at least:
                            - Insufficient settled funds (different from insufficient buying power)
                        Verification response messages with severity 25 include at least:
                            - This order is executable because the buy (or sell) limit is higher
                              (lower) than the ask (bid) price.
                        For the execution response, the orderReturnCode is typically 0 for a
                        successfully placed order.
                        Execution response messages with severity 30 include:
                            - Order Affirmation required (This means Schwab wants you to confirm
                              that you really meant to place this order as-is since something about
                              it meets Schwab's criteria for requiring verification. This is
                              usually analogous to a checkbox you would need to check when using
                              the web interface)
            affirm_order (bool) - Schwab requires additional verification for certain orders, such
                        as when a limit order is executable, or when buying some commodity ETFs.
                        Setting this to True will likely provide the verification needed to execute
                        these orders. You will likely also have to include the appropriate return
                        code in valid_return_codes.

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

        self.update_token(token_type='update')

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

        r = requests.post(urls.order_verification_v2(), json=data, headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)

        orderId = response['orderStrategy']['orderId']
        firstOrderLeg = response['orderStrategy']['orderLegs'][0]
        if "schwabSecurityId" in firstOrderLeg:
            data["OrderStrategy"]["OrderLegs"][0]["Instrument"]["ItemIssueId"] = firstOrderLeg["schwabSecurityId"]

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
        if affirm_order:
            data["OrderStrategy"]["OrderAffrmIn"] = True
        self.update_token(token_type='update')
        r = requests.post(urls.order_verification_v2(), json=data, headers=self.headers)

        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)

        messages = list()
        if "orderMessages" in response["orderStrategy"] and response["orderStrategy"]["orderMessages"] is not None:
            for message in response["orderStrategy"]["orderMessages"]:
                messages.append(message["message"])

        if response["orderStrategy"]["orderReturnCode"] in valid_return_codes:
            return messages, True

        return messages, False

    def cancel_order_v2(
            self, account_id, order_id,
            # The fields below are experimental and should only be changed if you know what
            # you're doing.
            instrument_type=46,
            ):
        """
        Cancels an open order (specified by order ID) using the v2 API

        account_id (int) - The account ID of the order. If the ID is XXXX-XXXX, we're looking for
            just XXXXXXXX.
        order_id (int) - The order ID as listed in orders_v2. The most recent order ID is likely:
            orders_v2(account_id=account_id)[0]['OrderList'][0]['OrderId'].
            Note: the order IDs listed in the v1 orders() are different
        instrument_type (int) - It is unclear what this means or when it should be different
        """
        data = {
            "TypeOfOrder": 0,
            "OrderManagementSystem": 2,
            "Orders": [{
                "OrderId": order_id,
                "IsLiveOrder": True,
                "InstrumentType": instrument_type,
                "CancelOrderLegs": [{}],
                }],
            "ContingentIdToCancel": 0,
            "OrderIdToCancel": 0,
            "OrderProcessingControl": 1,
            "ConfirmCancelOrderId": 0,
            }
        self.headers["schwab-client-account"] = account_id
        self.headers["schwab-resource-version"] = '2.0'
        # Web interface uses bearer token retrieved from:
        # https://client.schwab.com/api/auth/authorize/scope/api
        # and it seems to be good for 1800s (30min)
        self.update_token(token_type='api')
        r1 = requests.post(urls.cancel_order_v2(), json=data, headers=self.headers)
        if r1.status_code not in (200, 202):
            return [r1.text], False

        try:
            response = json.loads(r1.text)
            cancel_order_id = response['CancelOrderId']
        except (json.decoder.JSONDecodeError, KeyError):
            return [r1.text], False

        data['ConfirmCancelOrderId'] = cancel_order_id
        data['OrderProcessingControl'] = 2
        # Web interface uses bearer token retrieved from:
        # https://client.schwab.com/api/auth/authorize/scope/api
        # and it seems to be good for 1800s (30min)
        self.update_token(token_type='api')
        r2 = requests.post(urls.cancel_order_v2(), json=data, headers=self.headers)
        if r2.status_code not in (200, 202):
            return [r2.text], False
        try:
            response = json.loads(r2.text)
            if response["CancelOperationSuccessful"]:
                return response, True
        except (json.decoder.JSONDecodeError, KeyError):
            return [r2.text], False
        return response, False

    def quote_v2(self, tickers):
        """
        quote_v2 takes a list of Tickers, and returns Quote information through the Schwab API.
        """
        data = {
            "Symbols":tickers,
            "IsIra":False,
            "AccountRegType":"S3"
        }

        # Adding this header seems to be necessary.
        self.headers['schwab-resource-version'] = '1.0'

        self.update_token(token_type='update')
        r = requests.post(urls.ticker_quotes_v2(), json=data, headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)
        return response["quotes"]

    def orders_v2(self, account_id=None):
        """
        orders_v2 returns a list of orders for a Schwab Account. It is unclear to me how to filter by specific account.

        Currently, the query parameters are hard coded to return ALL orders, but this can be easily adjusted.
        """

        self.update_token(token_type='api')
        self.headers['schwab-resource-version'] = '2.0'
        if account_id:
            self.headers["schwab-client-account"] = account_id
        r = requests.get(urls.orders_v2(), headers=self.headers)
        if r.status_code != 200:
            return [r.text], False

        response = json.loads(r.text)
        return response["Orders"]

    def get_account_info_v2(self):
        account_info = dict()
        self.update_token(token_type='api')
        r = requests.get(urls.positions_v2(), headers=self.headers)
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
                            float(position["quantity"]),
                            0 if "costDetail" not in position else float(position["costDetail"]["costBasisDetail"]["costBasis"]),
                            0 if "priceDetail" not in position else float(position["priceDetail"]["marketValue"])
                        )._as_dict()
                    )
            account_info[int(account["accountId"])] = Account(
                account["accountId"],
                positions,
                account["totals"]["marketValue"],
                account["totals"]["cashInvestments"],
                account["totals"]["accountValue"],
                account["totals"].get("costBasis", 0)
            )._as_dict()

        return account_info

    def update_token(self, token_type='api'):
        r = self.session.get(f"https://client.schwab.com/api/auth/authorize/scope/{token_type}")
        if not r.ok:
            raise ValueError("Error updating Bearer token: {r.reason}")
        token = json.loads(r.text)['token']
        self.headers['authorization'] = f"Bearer {token}"

