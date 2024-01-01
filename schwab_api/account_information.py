class Account(dict):
    def __init__(self, account_id, positions, market_value, available_cash, account_value, cost_basis):
        self.account_id = account_id
        self.positions = positions
        self.market_value = market_value
        self.available_cash = available_cash
        self.account_value = account_value
        self.cost_basis = cost_basis

    def _as_dict(self):
        return {
            "account_id": self.account_id,
            "positions": self.positions,
            "market_value": self.market_value,
            "available_cash": self.available_cash,
            "account_value": self.account_value,
            "cost_basis": self.cost_basis,
        }

    def __repr__(self) -> str:
        return str(self._as_dict())
        
    def __str__(self) -> str:
        return str(self._as_dict())

class Position(dict):
    def __init__(self, symbol, description, quantity, cost, market_value):
        self.symbol = symbol
        self.description = description
        self.quantity = quantity
        self.cost = cost
        self.market_value = market_value

    def _as_dict(self):
        return {
            "symbol": self.symbol,
            "description": self.description,
            "quantity": self.quantity,
            "cost": self.cost,
            "market_value": self.market_value
        }

    def __repr__(self) -> str:
        return str(self._as_dict())

    def __str__(self) -> str:
        return str(self._as_dict())