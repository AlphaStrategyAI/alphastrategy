import pandas as pd
from alphastrategy.dsl.eval import evaluate_dsl, IllegalWeights


def test_equal_weight_two_symbols():
    bars = pd.DataFrame(
        {"AAPL": [1.0, 1.0], "MSFT": [1.0, 1.0]},
        index=pd.to_datetime(["2024-01-30", "2024-01-31"]),
    )
    dsl = {
        "dsl_version": "alphaloop.dsl/v0",
        "universe": ["AAPL", "MSFT"],
        "steps": [{"op": "equal_weight"}],
    }
    w = evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
    assert w == {"AAPL": 0.5, "MSFT": 0.5}


def test_unknown_op_raises():
    bars = pd.DataFrame(
        {"AAPL": [1.0], "MSFT": [1.0]},
        index=pd.to_datetime(["2024-01-31"]),
    )
    dsl = {
        "dsl_version": "alphaloop.dsl/v0",
        "universe": ["AAPL", "MSFT"],
        "steps": [{"op": "not_a_real_op"}],
    }
    try:
        evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
        assert False, "should have rejected unknown op"
    except (IllegalWeights, ValueError) as e:
        assert "not_a_real_op" in str(e)


def test_negative_weight_illegal():
    bars = pd.DataFrame(
        {"AAPL": [1.0], "MSFT": [1.0]},
        index=pd.to_datetime(["2024-01-31"]),
    )
    dsl = {
        "dsl_version": "alphaloop.dsl/v0",
        "universe": ["AAPL", "MSFT"],
        "steps": [{"op": "clip", "params": {"max": -0.1}}],
    }
    try:
        evaluate_dsl(dsl, bars, pd.Timestamp("2024-01-31"), {})
        assert False, "negative weights must be illegal"
    except IllegalWeights:
        pass


def test_momentum_12_1_rising_series_then_normalize():
    n = 280
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    prices = [100.0 + i for i in range(n)]
    bars = pd.DataFrame({"AAPL": prices}, index=dates)
    dsl = {
        "dsl_version": "alphaloop.dsl/v0",
        "universe": ["AAPL"],
        "steps": [{"op": "momentum_12_1"}, {"op": "normalize"}],
    }
    w = evaluate_dsl(dsl, bars, dates[-1], {})
    assert w == {"AAPL": 1.0}
