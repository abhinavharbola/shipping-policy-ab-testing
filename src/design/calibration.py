"""
Step 0.5: Calibrate simulation parameters from real Olist data.

This script computes descriptive statistics only: category-level AOV mean
and variance, seller-level AOV variance, baseline complaint rate, and the
distribution of orders per seller. Nothing here is a hypothesis test and
nothing here touches a treatment/control split, because at this point in
the project no such split exists yet. Output is a single JSON file that
power_analysis.py reads to size the experiment, and PREREGISTRATION.md
quotes directly.

Run this before writing PREREGISTRATION.md. Do not run it after.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = DATA / "calibration"
OUT.mkdir(parents=True, exist_ok=True)

COMPLAINT_THRESHOLD = 2  # review_score <= 2 counts as a delivery complaint
MIN_ORDERS_PER_CATEGORY = 200  # drop long-tail categories too thin to calibrate on


def load():
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv")
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
    reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
    products = pd.read_csv(RAW / "olist_products_dataset.csv")
    translation = pd.read_csv(RAW / "product_category_name_translation.csv")
    return orders, items, reviews, products, translation


def build_order_table(orders, items, reviews, products, translation, stats_out=None):
    orders = orders[orders["order_status"] == "delivered"].copy()

    order_value = items.groupby("order_id")["price"].sum().rename("aov")

    products = products.merge(translation, on="product_category_name", how="left")
    item_category = items.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id",
        how="left",
    )
    primary_category = (
        item_category.groupby("order_id")["product_category_name_english"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else np.nan)
        .rename("category")
    )

    # Olist orders can legitimately contain items from more than one seller.
    # Attributing an order's seller from a single item (rather than, e.g.,
    # the seller with the largest share of the order's value) is a real
    # simplification on real, non-simulated calibration data: multi-seller
    # orders get silently folded into whichever seller happened to log the
    # lowest order_item_id, which slightly understates each such seller's
    # true per-seller AOV variance. It's a small effect at this dataset's
    # scale, but it is a genuine distortion, not just an implementation
    # detail, so it's called out here rather than left implicit.
    order_seller_counts = items.groupby("order_id")["seller_id"].nunique()
    n_multi_seller_orders = int((order_seller_counts > 1).sum())
    if stats_out is not None:
        stats_out["n_multi_seller_orders"] = n_multi_seller_orders
        stats_out["n_multi_seller_orders_pct"] = round(
            100 * n_multi_seller_orders / len(order_seller_counts), 3
        )

    seller_of_order = (
        items.sort_values("order_item_id")
        .drop_duplicates("order_id")
        .set_index("order_id")["seller_id"]
        .rename("seller_id")
    )

    reviews_dedup = reviews.sort_values("review_answer_timestamp").drop_duplicates(
        "order_id", keep="last"
    )
    review_score = reviews_dedup.set_index("order_id")["review_score"].rename(
        "review_score"
    )

    table = (
        orders.set_index("order_id")
        .join(order_value, how="inner")
        .join(primary_category, how="left")
        .join(seller_of_order, how="left")
        .join(review_score, how="left")
        .dropna(subset=["aov", "category", "seller_id"])
    )
    table["complaint"] = (table["review_score"] <= COMPLAINT_THRESHOLD).astype(float)
    table.loc[table["review_score"].isna(), "complaint"] = np.nan
    return table


def calibrate(table):
    counts = table["category"].value_counts()
    keep_categories = counts[counts >= MIN_ORDERS_PER_CATEGORY].index.tolist()
    sub = table[table["category"].isin(keep_categories)]

    per_category = {}
    for cat, grp in sub.groupby("category"):
        reviewed = grp.dropna(subset=["complaint"])
        per_category[cat] = {
            "n_orders": int(len(grp)),
            "aov_mean": round(float(grp["aov"].mean()), 2),
            "aov_std": round(float(grp["aov"].std(ddof=1)), 2),
            "complaint_rate": round(float(reviewed["complaint"].mean()), 4),
            "n_reviewed": int(len(reviewed)),
        }

    weights = np.array([v["n_orders"] for v in per_category.values()], dtype=float)
    weights = weights / weights.sum()
    category_names = list(per_category.keys())

    overall_aov_mean = float(sub["aov"].mean())
    overall_aov_std = float(sub["aov"].std(ddof=1))
    overall_reviewed = sub.dropna(subset=["complaint"])
    overall_complaint_rate = float(overall_reviewed["complaint"].mean())

    seller_means = sub.groupby("seller_id")["aov"].mean()
    orders_per_seller = sub.groupby("seller_id").size()
    seller_level_aov_std = float(seller_means.std(ddof=1))
    calibration = {
        "source": "Olist Brazilian E-Commerce (olist_orders/items/reviews/products, "
        "delivered orders only). Used for descriptive calibration only; "
        "no hypothesis test is run on this data.",
        "complaint_definition": f"review_score <= {COMPLAINT_THRESHOLD}",
        "n_delivered_orders_used": int(len(sub)),
        "n_categories_kept": len(category_names),
        "category_names": category_names,
        "category_weights": dict(zip(category_names, weights.round(4).tolist())),
        "per_category": per_category,
        "overall": {
            "aov_mean": round(overall_aov_mean, 2),
            "aov_std": round(overall_aov_std, 2),
            "complaint_rate": round(overall_complaint_rate, 4),
        },
        "seller_level": {
            "n_real_sellers_in_scope": int(seller_means.shape[0]),
            "seller_level_aov_std": round(seller_level_aov_std, 2),
            "orders_per_seller_mean": round(float(orders_per_seller.mean()), 2),
            "orders_per_seller_median": float(orders_per_seller.median()),
            "orders_per_seller_p90": float(orders_per_seller.quantile(0.9)),
            "orders_per_seller_distribution": sorted(orders_per_seller.tolist()),
        },
    }
    return calibration


def main():
    orders, items, reviews, products, translation = load()
    data_quality_notes = {}
    table = build_order_table(
        orders, items, reviews, products, translation, stats_out=data_quality_notes
    )
    calibration = calibrate(table)
    calibration["data_quality_notes"] = data_quality_notes

    out_path = OUT / "calibration_params.json"
    with open(out_path, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"Wrote {out_path}")
    print(f"Categories kept: {calibration['n_categories_kept']}")
    print(f"Overall AOV mean/std: {calibration['overall']['aov_mean']} / "
          f"{calibration['overall']['aov_std']}")
    print(f"Overall complaint rate: {calibration['overall']['complaint_rate']}")
    print(
        f"Multi-seller orders (seller attributed to lowest order_item_id): "
        f"{data_quality_notes['n_multi_seller_orders']} "
        f"({data_quality_notes['n_multi_seller_orders_pct']}%)"
    )
    print(f"Seller-level AOV std (between-seller): "
          f"{calibration['seller_level']['seller_level_aov_std']}")
    print(f"Median orders per seller: "
          f"{calibration['seller_level']['orders_per_seller_median']}")


if __name__ == "__main__":
    main()
