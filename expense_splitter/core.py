"""Core logic. All money is integer minor units (paise/cents) to avoid float drift."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def to_minor(amount) -> int:
    """Convert '12.34' / 12.34 / Decimal to integer minor units."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def fmt(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    return f"{sign}{abs(minor) // 100}.{abs(minor) % 100:02d}"


def split_equal(total: int, people: list[str]) -> dict[str, int]:
    """Equal split; leftover minor units go one each to the first people."""
    if not people or len(set(people)) != len(people):
        raise ValueError("people must be a non-empty list of unique names")
    base, extra = divmod(total, len(people))
    return {p: base + (1 if i < extra else 0) for i, p in enumerate(people)}


def split_exact(total: int, shares: dict[str, int]) -> dict[str, int]:
    if sum(shares.values()) != total:
        raise ValueError(f"exact shares sum to {fmt(sum(shares.values()))}, expected {fmt(total)}")
    if any(v < 0 for v in shares.values()):
        raise ValueError("shares cannot be negative")
    return dict(shares)


def split_percent(total: int, percents: dict[str, float]) -> dict[str, int]:
    """Percent split using the largest-remainder method so shares always sum to total."""
    pct = {p: Decimal(str(v)) for p, v in percents.items()}
    if sum(pct.values()) != 100:
        raise ValueError(f"percentages sum to {sum(pct.values())}, expected 100")
    raw = {p: Decimal(total) * v / 100 for p, v in pct.items()}
    out = {p: int(r) for p, r in raw.items()}
    leftover = total - sum(out.values())
    for p in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:leftover]:
        out[p] += 1
    return out


@dataclass
class Expense:
    description: str
    paid_by: str
    total: int
    shares: dict[str, int]


@dataclass
class Ledger:
    expenses: list[Expense] = field(default_factory=list)

    def add(self, description: str, paid_by: str, amount, mode: str = "equal",
            participants=None, split=None) -> Expense:
        """mode: equal (participants=[...]), exact (split={name: amt}), percent (split={name: pct})."""
        total = to_minor(amount)
        if total <= 0:
            raise ValueError("amount must be positive")
        if mode == "equal":
            shares = split_equal(total, list(participants or []))
        elif mode == "exact":
            shares = split_exact(total, {p: to_minor(v) for p, v in (split or {}).items()})
        elif mode == "percent":
            shares = split_percent(total, split or {})
        else:
            raise ValueError(f"unknown split mode: {mode}")
        exp = Expense(description, paid_by, total, shares)
        self.expenses.append(exp)
        return exp

    def balances(self) -> dict[str, int]:
        """Net balance per person: positive = is owed money, negative = owes money."""
        bal: dict[str, int] = {}
        for e in self.expenses:
            bal[e.paid_by] = bal.get(e.paid_by, 0) + e.total
            for p, s in e.shares.items():
                bal[p] = bal.get(p, 0) - s
        return bal

    def settle(self) -> list[tuple[str, str, int]]:
        return settle(self.balances())

    def to_dict(self) -> dict:
        return {"expenses": [e.__dict__ for e in self.expenses]}

    @classmethod
    def from_dict(cls, data: dict) -> "Ledger":
        return cls([Expense(**e) for e in data.get("expenses", [])])


def settle(balances: dict[str, int]) -> list[tuple[str, str, int]]:
    """Return (debtor, creditor, amount) transfers that clear all balances.

    Greedy: repeatedly match the largest debtor with the largest creditor. Each transfer
    fully clears at least one person, so there are at most n-1 transfers.
    """
    if sum(balances.values()) != 0:
        raise ValueError("balances must sum to zero")
    debtors = [list(x) for x in sorted(((-b, p) for p, b in balances.items() if b < 0), reverse=True)]
    creditors = [list(x) for x in sorted(((b, p) for p, b in balances.items() if b > 0), reverse=True)]
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amt = min(debtors[i][0], creditors[j][0])
        transfers.append((debtors[i][1], creditors[j][1], amt))
        debtors[i][0] -= amt
        creditors[j][0] -= amt
        if debtors[i][0] == 0:
            i += 1
        if creditors[j][0] == 0:
            j += 1
    return transfers
