import pytest
import sys
import os

backend_dir = os.path.join(os.path.dirname(__file__), "..")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from services.reward_engine import reward_engine

def test_funded_money_calculation_worked_example():
    """
    Worked example from specification:
    Milestone = Rs 1,00,000
    Weights: Priya (1) = 0.5, Arun (2) = 0.3, Meera (3) = 0.2
    Expected: Priya = 25,783, Arun = 18,643, Meera = 15,074, Expert = 25,500
    Total sum = 1,00,000
    """
    milestone_budget = 100000
    weights = {1: 0.5, 2: 0.3, 3: 0.2}

    res = reward_engine.calculate_money_payout(
        milestone_budget=milestone_budget,
        student_weights=weights,
        fee_pct=10.0,
        ai_reserve_pct=5.0,
        expert_pct_of_remainder=30.0,
        student_equal_pct=40.0
    )

    assert res["fee"] == 10000
    assert res["ai_reserve"] == 5000
    assert res["expert_share"] == 25500

    student_payouts = res["student_payouts"]
    assert student_payouts[1] == 25783
    assert student_payouts[2] == 18643
    assert student_payouts[3] == 15074

    assert res["total"] == 100000

def test_credit_mode_worked_example():
    """
    Worked example from specification:
    Credit Pool = 100 CU
    Weights: Priya (1) = 0.5, Arun (2) = 0.3, Meera (3) = 0.2
    Expected: Priya = 36.0 CU, Arun = 24.8 CU, Meera = 19.2 CU, Expert = 20.0 CU
    Total sum = 100.0 CU
    """
    credit_pool = 100.0
    weights = {1: 0.5, 2: 0.3, 3: 0.2}

    res = reward_engine.calculate_credit_payout(
        credit_pool_cu=credit_pool,
        student_weights=weights,
        expert_pct=20.0,
        student_equal_pct=30.0
    )

    assert res["expert_cu"] == 20.0
    payouts = res["student_payouts_cu"]
    assert payouts[1] == 36.0
    assert payouts[2] == 24.8
    assert payouts[3] == 19.2
    assert res["total_cu"] == 100.0

def test_rounding_ties():
    """Verifies that integer rounding ties sum up exactly to the milestone budget."""
    milestone_budget = 50000
    weights = {1: 0.333, 2: 0.333, 3: 0.334}
    res = reward_engine.calculate_money_payout(
        milestone_budget=milestone_budget,
        student_weights=weights
    )
    assert res["total"] == 50000
