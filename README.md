# expense-splitter

A small Splitwise-style engine: log shared expenses (equal, exact or percentage splits), see who is up or down, and settle the whole group with **as few payments as possible**. Pure Python, zero runtime dependencies.

## The product problem

Group trips and shared flats generate dozens of small IOUs. Left alone, people end up with a web of "A owes B, B owes C, C owes A" debts, so settling takes many UPI transfers and nobody trusts the numbers. The jobs to be done:

1. **Record fast** - one line per expense, whoever paid, any split style.
2. **Trust the maths** - balances must always sum to exactly zero, with no floating-point drift or lost paise.
3. **Settle with minimum friction** - fewer transfers means fewer reminders and less awkward chasing.

## Quickstart

```bash
pip install -e ".[dev]"
splitter add "Hotel" 3000 --paid-by asha --equal asha ravi meera
splitter add "Cab" 450.50 --paid-by ravi --percent asha=50 ravi=30 meera=20
splitter add "Snacks" 600 --paid-by meera --exact asha=200 ravi=200 meera=200
splitter balances
splitter settle
pytest
```

The ledger is stored in `ledger.json` (override with `--file`).

## How it works

- **Money as integers.** Amounts are converted to minor units (paise) with `Decimal`, so `0.1 + 0.2 == 0.3`.
- **Rounding.** Equal splits give leftover paise one each to the first participants. Percent splits use the *largest remainder method*, so every share sums exactly to the total.
- **Net balance** = total paid - total owed. Balances across a group always sum to zero.
- **Settlement.** Greedy matching: pair the largest debtor with the largest creditor, transfer `min(debt, credit)`, repeat. Each transfer fully clears at least one person, so at most `n - 1` payments are needed for `n` people. Finding the true global minimum is NP-hard in general (it equals partitioning people into the maximum number of zero-sum groups), so this is the standard near-optimal heuristic. It is optimal whenever no sub-group already nets to zero by itself.

## Structure

```
expense_splitter/core.py   splits, ledger, balances, settle()
expense_splitter/cli.py    `splitter` command
tests/test_core.py         rounding, zero-sum, randomized property tests, CLI
```

## Roadmap

- Exact minimum via zero-sum subset grouping
- Multi-currency with stored FX rates
- Share-by-weight splits and expense editing/deletion
- UPI deep links for suggested payments
- Small web UI

## License

MIT
