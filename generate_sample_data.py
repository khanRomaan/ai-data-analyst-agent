"""Generates a realistic synthetic e-commerce sales dataset for testing
the AI Data Analyst Agent."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

PRODUCTS = {
    "Wireless Mouse": ("Electronics", 19.99),
    "Mechanical Keyboard": ("Electronics", 79.99),
    "USB-C Hub": ("Electronics", 34.99),
    "Noise Cancelling Headphones": ("Electronics", 149.99),
    "Webcam HD": ("Electronics", 44.99),
    "Standing Desk": ("Furniture", 349.99),
    "Ergonomic Chair": ("Furniture", 229.99),
    "Monitor Arm": ("Furniture", 59.99),
    "Desk Lamp": ("Furniture", 24.99),
    "Bookshelf": ("Furniture", 89.99),
    "Yoga Mat": ("Fitness", 29.99),
    "Adjustable Dumbbells": ("Fitness", 129.99),
    "Resistance Bands": ("Fitness", 14.99),
    "Water Bottle": ("Fitness", 12.99),
    "Foam Roller": ("Fitness", 19.99),
    "Notebook Set": ("Office Supplies", 9.99),
    "Sticky Notes Pack": ("Office Supplies", 4.99),
    "Fountain Pen": ("Office Supplies", 22.99),
    "Whiteboard": ("Office Supplies", 39.99),
    "Stapler": ("Office Supplies", 8.99),
}
PRODUCT_NAMES = list(PRODUCTS.keys())
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America"]
CHANNELS = ["Online", "Retail Partner", "Direct Sales"]

# 2 full years of daily orders so we have several complete quarters
start = pd.Timestamp("2024-01-01")
end = pd.Timestamp("2025-09-19")  # "today" in this scenario
n_rows = 8000

dates = start + pd.to_timedelta(rng.integers(0, (end - start).days, n_rows), unit="D")

# give each product a rough popularity weight so results are interesting
weights = rng.dirichlet(np.ones(len(PRODUCT_NAMES)) * 1.5)

rows = []
for i in range(n_rows):
    product = rng.choice(PRODUCT_NAMES, p=weights)
    category, base_price = PRODUCTS[product]
    qty = int(rng.integers(1, 6))
    # small random price variation (discounts/promos)
    price = round(base_price * rng.uniform(0.85, 1.05), 2)
    region = rng.choice(REGIONS, p=[0.4, 0.28, 0.22, 0.10])
    channel = rng.choice(CHANNELS, p=[0.6, 0.25, 0.15])
    rows.append({
        "order_id": f"ORD-{100000+i}",
        "order_date": dates[i].date().isoformat(),
        "product": product,
        "category": category,
        "region": region,
        "sales_channel": channel,
        "quantity": qty,
        "unit_price": price,
        "revenue": round(qty * price, 2),
        "customer_id": f"CUST-{rng.integers(1000, 4000)}",
    })

df = pd.DataFrame(rows).sort_values("order_date").reset_index(drop=True)
df.to_csv("/home/claude/ai_data_analyst/sample_sales_data.csv", index=False)
print(df.shape)
print(df.head())
print(df["order_date"].min(), "->", df["order_date"].max())
