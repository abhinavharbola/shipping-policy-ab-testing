"""
Regression test for a real bug: calibrate() previously computed only one
set of category weights, an order-level share, and simulate.py used that
same distribution to draw a simulated SELLER's category. That conflates
units: a seller placing many orders in one category counted many times
toward that category's weight instead of once. calibrate() now also
emits seller-level weights (each category's share of sellers), which is
the correct distribution for that draw.
"""

import numpy as np
import pandas as pd

from design.calibration import calibrate


def make_fake_table():
    """
    Category 'a': one high-volume seller with 300 orders.
    Category 'b': fifty low-volume sellers with 4 orders each (200 orders).
    Order-level weights should favor 'a' (300 vs 200 orders); seller-level
    weights should favor 'b' (50 sellers vs 1), the opposite ranking.
    """
    rows = []
    for _ in range(300):
        rows.append({
            "seller_id": "seller_a_0",
            "category": "a",
            "aov": 100.0,
            "complaint": 0.0,
        })
    for i in range(50):
        for _ in range(4):
            rows.append({
                "seller_id": f"seller_b_{i}",
                "category": "b",
                "aov": 100.0,
                "complaint": 0.0,
            })
    return pd.DataFrame(rows)


def test_order_level_and_seller_level_weights_disagree_by_construction():
    table = make_fake_table()
    calibration = calibrate(table)

    order_weights = calibration["category_weights"]
    seller_weights = calibration["category_weights_seller_level"]

    assert order_weights["a"] > order_weights["b"]
    assert seller_weights["b"] > seller_weights["a"]


def test_seller_level_weights_sum_to_one_and_match_seller_counts():
    table = make_fake_table()
    calibration = calibrate(table)
    seller_weights = calibration["category_weights_seller_level"]

    assert np.isclose(sum(seller_weights.values()), 1.0)
    # 1 seller in 'a', 50 sellers in 'b', 51 total
    assert np.isclose(seller_weights["a"], 1 / 51, atol=1e-3)
    assert np.isclose(seller_weights["b"], 50 / 51, atol=1e-3)
