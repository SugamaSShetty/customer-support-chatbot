from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import os
import math

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    orders = pd.read_csv(os.path.join(BASE_DIR, "../orders.csv"))
    order_items = pd.read_csv(os.path.join(BASE_DIR, "../order_items.csv"))
    products = pd.read_csv(os.path.join(BASE_DIR, "../products.csv"))
    inventory = pd.read_csv(os.path.join(BASE_DIR, "../inventory_items.csv"), on_bad_lines='skip')
    print("Inventory Columns:", inventory.columns.tolist())

except Exception as e:
    raise RuntimeError(f"Failed to load one or more CSV files: {e}")

# Clean data
orders = orders.fillna(value=pd.NA)
order_items = order_items.fillna(value=pd.NA)
products = products.fillna(value=pd.NA)
inventory = inventory.fillna(value=pd.NA)

# Standardize column names
orders.columns = orders.columns.str.lower()
order_items.columns = order_items.columns.str.lower()
products.columns = products.columns.str.lower()
inventory.columns = inventory.columns.str.lower()

@app.get("/")
def read_root():
    return {"message": "Customer Support Chatbot API running!"}

@app.get("/top-products")
def top_products():
    if "product_id" not in order_items.columns or "id" not in products.columns:
        return {"error": "Required columns missing for merging order_items and products."}

    merged = pd.merge(order_items, products, left_on="product_id", right_on="id")
    name_column = "name" if "name" in merged.columns else "product_name" if "product_name" in merged.columns else None

    if not name_column:
        return {"error": "Product name column not found in merged data."}

    product_counts = merged[name_column].value_counts().head(5)
    return {"top_5_products": product_counts.to_dict()}

@app.get("/product-stock/{product_name}")
def product_stock(product_name: str):
    possible_columns = ["product_name", "name"]
    name_col = next((col for col in possible_columns if col in inventory.columns), None)

    if not name_col:
        return {"error": "Column 'product_name' not found in inventory."}

    matching_rows = inventory[inventory[name_col].str.lower().str.contains(product_name.lower(), na=False)]

    if matching_rows.empty:
        return {"error": f"No products matching '{product_name}' found in inventory."}

    result = matching_rows[name_col].value_counts().to_dict()
    return {
        "query": product_name,
        "matched_products": result
    }

@app.get("/order-status/{order_id}")
def order_status(order_id: int):
    if "order_id" not in orders.columns:
        return {"error": "Order ID column not found in orders data."}

    order = orders[orders["order_id"] == order_id]
    if order.empty:
        return {"error": f"Order ID {order_id} not found"}

    def clean(value):
        return None if pd.isna(value) or (isinstance(value, float) and math.isnan(value)) else value

    return JSONResponse(content={
        "order_id": int(order_id),
        "status": clean(order.iloc[0].get("status")),
        "shipped_at": clean(order.iloc[0].get("shipped_at")),
        "delivered_at": clean(order.iloc[0].get("delivered_at")),
        "returned_at": clean(order.iloc[0].get("returned_at")),
    })
