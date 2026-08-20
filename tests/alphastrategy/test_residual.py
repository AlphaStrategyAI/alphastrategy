from alphastrategy.supervisor.residual import residual_book


def test_residual_subtracts_killed_sleeve_and_drops_zeros():
    combined = {"AAPL": 0.15, "MSFT": 0.15}
    killed = {"AAPL": 0.15}
    assert residual_book(combined, killed) == {"MSFT": 0.15}


def test_residual_overlapping_name_keeps_other_sleeve_share():
    combined = {"AAPL": 0.20}
    killed = {"AAPL": 0.10}
    assert residual_book(combined, killed) == {"AAPL": 0.10}


def test_residual_drops_negative_noise():
    assert residual_book({"AAPL": 0.1}, {"AAPL": 0.1}) == {}
