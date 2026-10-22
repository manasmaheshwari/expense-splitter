import json
import random

import pytest

from expense_splitter import Ledger, settle, split_equal, split_exact, split_percent
from expense_splitter.cli import main
from expense_splitter.core import to_minor


def test_equal_split_rounding_conserves_total():
    shares = split_equal(10000, ["a", "b", "c"])  # 100.00 / 3
    assert sum(shares.values()) == 10000
    assert sorted(shares.values()) == [3333, 3333, 3334]


def test_exact_split_must_sum():
    with pytest.raises(ValueError):
        split_exact(1000, {"a": 400, "b": 500})
    assert split_exact(1000, {"a": 400, "b": 600}) == {"a": 400, "b": 600}


def test_percent_split_largest_remainder():
    shares = split_percent(1000, {"a": 33.33, "b": 33.33, "c": 33.34})
    assert sum(shares.values()) == 1000
    assert split_percent(100, {"a": 50, "b": 50}) == {"a": 50, "b": 50}


def test_percent_must_total_100():
    with pytest.raises(ValueError):
        split_percent(1000, {"a": 60, "b": 30})


def test_to_minor_avoids_float_error():
    assert to_minor("0.1") + to_minor("0.2") == to_minor("0.3")
    assert to_minor(19.99) == 1999


def test_balances_zero_sum_and_values():
    ledger = Ledger()
    ledger.add("dinner", "a", "90", participants=["a", "b", "c"])
    ledger.add("cab", "b", "30", "exact", split={"a": 10, "b": 10, "c": 10})
    bal = ledger.balances()
    assert sum(bal.values()) == 0
    assert bal == {"a": 9000 - 3000 - 1000, "b": -3000 + 3000 - 1000, "c": -3000 - 1000}


def test_settle_minimises_transactions():
    # a owed 50, b owed 30, c owes 40, d owes 40 -> 3 transfers, not 4
    t = settle({"a": 5000, "b": 3000, "c": -4000, "d": -4000})
    assert len(t) == 3
    net = {}
    for d, c, amt in t:
        net[d] = net.get(d, 0) - amt
        net[c] = net.get(c, 0) + amt
    assert net == {"a": 5000, "b": 3000, "c": -4000, "d": -4000}


def test_settle_empty_and_nonzero():
    assert settle({"a": 0, "b": 0}) == []
    with pytest.raises(ValueError):
        settle({"a": 100})


def test_settle_random_properties():
    rng = random.Random(7)
    for _ in range(200):
        n = rng.randint(2, 8)
        vals = [rng.randint(-5000, 5000) for _ in range(n - 1)]
        vals.append(-sum(vals))
        bal = {f"p{i}": v for i, v in enumerate(vals)}
        t = settle(bal)
        assert len(t) <= n - 1
        for d, c, amt in t:
            assert amt > 0
            bal[d] += amt
            bal[c] -= amt
        assert all(v == 0 for v in bal.values())


def test_rejects_bad_input():
    ledger = Ledger()
    with pytest.raises(ValueError):
        ledger.add("x", "a", "0", participants=["a"])
    with pytest.raises(ValueError):
        split_equal(100, ["a", "a"])


def test_cli_roundtrip(tmp_path, capsys):
    f = str(tmp_path / "l.json")
    assert main(["--file", f, "add", "Hotel", "300", "--paid-by", "asha", "--equal", "asha", "ravi", "meera"]) == 0
    assert main(["--file", f, "add", "Cab", "50", "--paid-by", "ravi", "--percent", "asha=50", "ravi=50"]) == 0
    assert json.loads(open(f).read())["expenses"]
    capsys.readouterr()
    assert main(["--file", f, "settle"]) == 0
    out = capsys.readouterr().out
    assert "meera pays asha 100.00" in out
    assert main(["--file", f, "add", "Bad", "10", "--paid-by", "a", "--exact", "a=3"]) == 1
