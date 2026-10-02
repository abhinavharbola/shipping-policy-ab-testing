import pandas as pd

from design.calibration import build_order_table


def make_frames():
    orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_status": ["delivered", "delivered", "delivered", "shipped"],
    })
    items = pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o3"],
        "order_item_id": [1, 2, 1, 1],
        "product_id": ["p1", "p1", "p2", "p3"],
        "seller_id": ["s1", "s2", "s1", "s3"],
        "price": [100.0, 50.0, 80.0, 60.0],
        "freight_value": [10.0, 5.0, 20.0, 8.0],
    })
    reviews = pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "review_score": [1, 5, 4],
        "review_answer_timestamp": ["2020-01-01"] * 3,
    })
    products = pd.DataFrame({
        "product_id": ["p1", "p2", "p3"],
        "product_category_name": ["a", "b", None],
    })
    translation = pd.DataFrame({
        "product_category_name": ["a", "b"],
        "product_category_name_english": ["cat_a", "cat_b"],
    })
    return orders, items, reviews, products, translation


def test_freight_is_summed_per_order():
    table = build_order_table(*make_frames())
    assert table.loc["o1", "freight"] == 15.0
    assert table.loc["o2", "freight"] == 20.0


def test_orders_missing_a_category_are_dropped_and_counted():
    stats = {}
    table = build_order_table(*make_frames(), stats_out=stats)
    assert "o3" not in table.index
    assert stats["n_orders_dropped_missing_category_or_seller"] == 1


def test_multi_seller_orders_are_counted_and_credited_to_the_lowest_item_seller():
    stats = {}
    table = build_order_table(*make_frames(), stats_out=stats)
    assert stats["n_multi_seller_orders"] == 1
    assert table.loc["o1", "seller_id"] == "s1"
    assert table.loc["o1", "aov"] == 150.0


def test_non_delivered_orders_are_excluded():
    table = build_order_table(*make_frames())
    assert "o4" not in table.index
