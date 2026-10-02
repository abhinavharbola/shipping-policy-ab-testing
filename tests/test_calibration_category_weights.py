import numpy as np
import pandas as pd

from design.calibration import calibrate


def make_fake_table():
    rows = []
    for _ in range(300):
        rows.append({
            "seller_id": "seller_a_0",
            "category": "a",
            "aov": 100.0,
            "freight": 20.0,
            "complaint": 0.0,
        })
    for i in range(50):
        for _ in range(4):
            rows.append({
                "seller_id": f"seller_b_{i}",
                "category": "b",
                "aov": 100.0,
                "freight": 20.0,
                "complaint": 0.0,
            })
    return pd.DataFrame(rows)


def test_order_level_and_seller_level_weights_disagree_by_construction():
    calibration = calibrate(make_fake_table())
    order_weights = calibration["category_weights"]
    seller_weights = calibration["category_weights_seller_level"]

    assert order_weights["a"] > order_weights["b"]
    assert seller_weights["b"] > seller_weights["a"]


def test_seller_level_weights_sum_to_one_and_match_seller_counts():
    calibration = calibrate(make_fake_table())
    seller_weights = calibration["category_weights_seller_level"]

    assert np.isclose(sum(seller_weights.values()), 1.0)
    assert np.isclose(seller_weights["a"], 1 / 51, atol=1e-3)
    assert np.isclose(seller_weights["b"], 50 / 51, atol=1e-3)


def test_calibration_reports_mean_freight_per_order():
    calibration = calibrate(make_fake_table())
    assert calibration["overall"]["freight_mean_per_order"] == 20.0
