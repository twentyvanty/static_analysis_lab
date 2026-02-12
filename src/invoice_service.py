from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

VALID_CATEGORIES = {"book", "food", "electronics", "other"}
FRAGILE_FEE_PER_ITEM = 5.0


@dataclass
class LineItem:
    sku: str
    category: str
    unit_price: float
    qty: int
    fragile: bool = False


@dataclass
class Invoice:
    invoice_id: str
    customer_id: str
    country: str
    membership: str
    coupon: Optional[str]
    items: List[LineItem]


class InvoiceService:
    SHIPPING_RULES = {
        "TH": [(500, 60), (float("inf"), 0)],
        "JP": [(4000, 600), (float("inf"), 0)],
        "US": [(100, 15), (300, 8), (float("inf"), 0)],
        "DEFAULT": [(200, 25), (float("inf"), 0)],
    }

    TAX_RATE = {
        "TH": 0.07,
        "JP": 0.10,
        "US": 0.08,
        "DEFAULT": 0.05,
    }

    MEMBERSHIP_RATE = {
        "gold": 0.03,
        "platinum": 0.05,
    }

    def __init__(self) -> None:
        self._coupon_rate: Dict[str, float] = {
            "WELCOME10": 0.10,
            "VIP20": 0.20,
            "STUDENT5": 0.05,
        }

    # ------------------------
    # Validation
    # ------------------------
    def _validate(self, inv: Invoice) -> List[str]:
        if inv is None:
            return ["Invoice is missing"]

        problems: List[str] = []

        if not inv.invoice_id:
            problems.append("Missing invoice_id")
        if not inv.customer_id:
            problems.append("Missing customer_id")
        if not inv.items:
            problems.append("Invoice must contain items")

        for it in inv.items:
            if not it.sku:
                problems.append("Item sku is missing")
            if it.qty <= 0:
                problems.append(f"Invalid qty for {it.sku}")
            if it.unit_price < 0:
                problems.append(f"Invalid price for {it.sku}")
            if it.category not in VALID_CATEGORIES:
                problems.append(f"Unknown category for {it.sku}")

        return problems

    # ------------------------
    # Small helper methods (reduces complexity)
    # ------------------------
    @staticmethod
    def _subtotal(items: List[LineItem]) -> float:
        return sum(it.unit_price * it.qty for it in items)

    @staticmethod
    def _fragile_fee(items: List[LineItem]) -> float:
        return sum(FRAGILE_FEE_PER_ITEM * it.qty for it in items if it.fragile)

    def _shipping(self, country: str, subtotal: float) -> float:
        rules = self.SHIPPING_RULES.get(country, self.SHIPPING_RULES["DEFAULT"])
        for limit, fee in rules:
            if subtotal < limit:
                return fee
        return 0.0

    def _tax(self, country: str, taxable: float) -> float:
        rate = self.TAX_RATE.get(country, self.TAX_RATE["DEFAULT"])
        return taxable * rate

    def _membership_discount(self, membership: str, subtotal: float) -> float:
        rate = self.MEMBERSHIP_RATE.get(membership)
        if rate:
            return subtotal * rate
        if subtotal > 3000:
            return 20.0
        return 0.0

    def _coupon_discount(self, coupon: Optional[str], subtotal: float, warnings: List[str]) -> float:
        if not coupon:
            return 0.0

        code = coupon.strip()
        if code in self._coupon_rate:
            return subtotal * self._coupon_rate[code]

        warnings.append("Unknown coupon")
        return 0.0

    # ------------------------
    # Main method (NOW SIMPLE)
    # ------------------------
    def compute_total(self, inv: Invoice) -> Tuple[float, List[str]]:
        problems = self._validate(inv)
        if problems:
            raise ValueError("; ".join(problems))

        warnings: List[str] = []

        subtotal = self._subtotal(inv.items)
        fragile_fee = self._fragile_fee(inv.items)

        shipping = self._shipping(inv.country, subtotal)

        discount = (
            self._membership_discount(inv.membership, subtotal)
            + self._coupon_discount(inv.coupon, subtotal, warnings)
        )

        taxable = subtotal - discount
        tax = self._tax(inv.country, taxable)

        total = max(subtotal + shipping + fragile_fee + tax - discount, 0.0)

        if subtotal > 10000 and inv.membership not in self.MEMBERSHIP_RATE:
            warnings.append("Consider membership upgrade")

        return total, warnings
