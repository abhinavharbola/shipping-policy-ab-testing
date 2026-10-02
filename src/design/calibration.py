import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = DATA / "calibration"

COMPLAINT_THRESHOLD = 2
MIN_ORDERS_PER_CATEGORY = 200


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
    order_freight = items.groupby("order_id")["freight_value"].sum().rename("freight")

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

    joined = (
        orders.set_index("order_id")
        .join(order_value, how="inner")
        .join(order_freight, how="left")
        .join(primary_category, how="left")
        .join(seller_of_order, how="left")
        .join(review_score, how="left")
    )
    table = joined.dropna(subset=["aov", "category", "seller_id"])
    if stats_out is not None:
        stats_out["n_orders_dropped_missing_category_or_seller"] = int(
            len(joined) - len(table)
        )

    table = table.copy()
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
    overall_freight_mean = float(sub["freight"].mean())
    overall_reviewed = sub.dropna(subset=["complaint"])
    overall_complaint_rate = float(overall_reviewed["complaint"].mean())

    seller_means = sub.groupby("seller_id")["aov"].mean()
    orders_per_seller = sub.groupby("seller_id").size()
    seller_level_aov_std = float(seller_means.std(ddof=1))

    seller_primary_category = sub.groupby("seller_id")["category"].agg(
        lambda s: s.mode().iloc[0]
    )
    seller_category_counts = seller_primary_category.value_counts().reindex(
        category_names, fill_value=0
    )
    seller_weights = seller_category_counts.astype(float)
    seller_weights = seller_weights / seller_weights.sum()

    return {
        "source": "Olist Brazilian E-Commerce (olist_orders/items/reviews/products, "
        "delivered orders only). Used for descriptive calibration only; "
        "no hypothesis test is run on this data.",
        "complaint_definition": f"review_score <= {COMPLAINT_THRESHOLD}",
        "n_delivered_orders_used": int(len(sub)),
        "n_categories_kept": len(category_names),
        "category_names": category_names,
        "category_weights": dict(zip(category_names, weights.round(4).tolist())),
        "category_weights_note": "Order-level: each category's share of "
        "kept orders. Kept for descriptive reference; simulate.py uses "
        "category_weights_seller_level to draw a simulated seller's "
        "category, since the unit being drawn is a seller, not an order.",
        "category_weights_seller_level": dict(
            zip(category_names, seller_weights.round(4).tolist())
        ),
        "per_category": per_category,
        "overall": {
            "aov_mean": round(overall_aov_mean, 2),
            "aov_std": round(overall_aov_std, 2),
            "freight_mean_per_order": round(overall_freight_mean, 2),
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


def main():
    orders, items, reviews, products, translation = load()
    data_quality_notes = {}
    table = build_order_table(
        orders, items, reviews, products, translation, stats_out=data_quality_notes
    )
    calibration = calibrate(table)
    calibration["data_quality_notes"] = data_quality_notes

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "calibration_params.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)

    print(f"Wrote {out_path}")
    print(f"Categories kept: {calibration['n_categories_kept']}")
    print(
        f"Overall AOV mean/std: {calibration['overall']['aov_mean']} / "
        f"{calibration['overall']['aov_std']}"
    )
    print(f"Mean freight per order: {calibration['overall']['freight_mean_per_order']}")
    print(f"Overall complaint rate: {calibration['overall']['complaint_rate']}")
    print(
        f"Multi-seller orders (whole order credited to the seller of the lowest "
        f"order_item_id): {data_quality_notes['n_multi_seller_orders']} "
        f"({data_quality_notes['n_multi_seller_orders_pct']}%)"
    )
    print(
        f"Orders dropped for missing category or seller: "
        f"{data_quality_notes['n_orders_dropped_missing_category_or_seller']}"
    )
    print(
        f"Seller-level AOV std (between-seller): "
        f"{calibration['seller_level']['seller_level_aov_std']}"
    )
    print(
        f"Median orders per seller: "
        f"{calibration['seller_level']['orders_per_seller_median']}"
    )


if __name__ == "__main__":
    main()
