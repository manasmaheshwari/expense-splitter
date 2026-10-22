import argparse
import json
import sys
from pathlib import Path

from .core import Ledger, fmt


def _load(path: Path) -> Ledger:
    return Ledger.from_dict(json.loads(path.read_text())) if path.exists() else Ledger()


def _pairs(items):
    out = {}
    for item in items:
        name, _, val = item.partition("=")
        if not val:
            raise ValueError(f"expected NAME=VALUE, got '{item}'")
        out[name] = val
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="splitter", description="Split expenses, settle with fewer payments.")
    ap.add_argument("--file", default="ledger.json", type=Path, help="ledger file (default ledger.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add an expense")
    a.add_argument("description")
    a.add_argument("amount")
    a.add_argument("--paid-by", required=True)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--equal", nargs="+", metavar="NAME", help="split equally among these people")
    g.add_argument("--exact", nargs="+", metavar="NAME=AMT", help="exact amounts")
    g.add_argument("--percent", nargs="+", metavar="NAME=PCT", help="percentages summing to 100")
    sub.add_parser("balances", help="show net balances")
    sub.add_parser("settle", help="show minimum payments to settle up")
    args = ap.parse_args(argv)

    try:
        ledger = _load(args.file)
        if args.cmd == "add":
            if args.equal:
                ledger.add(args.description, args.paid_by, args.amount, "equal", participants=args.equal)
            elif args.exact:
                ledger.add(args.description, args.paid_by, args.amount, "exact", split=_pairs(args.exact))
            else:
                ledger.add(args.description, args.paid_by, args.amount, "percent", split=_pairs(args.percent))
            args.file.write_text(json.dumps(ledger.to_dict(), indent=2))
            print(f"Added: {args.description} ({args.amount}) paid by {args.paid_by}")
        elif args.cmd == "balances":
            for p, b in sorted(ledger.balances().items()):
                label = "gets back" if b > 0 else "owes" if b < 0 else "settled"
                print(f"{p:<12} {label:<10} {fmt(abs(b))}")
        else:
            transfers = ledger.settle()
            for d, c, amt in transfers:
                print(f"{d} pays {c} {fmt(amt)}")
            if not transfers:
                print("All settled.")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
