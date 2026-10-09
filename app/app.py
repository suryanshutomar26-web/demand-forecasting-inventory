
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st




st.set_page_config(
    page_title="Demand Forecasting & Inventory Optimization",
    page_icon="📦",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"




@st.cache_data
def load_data():
    history = pd.read_csv(DATA_DIR / "historical_sales.csv")
    forecasts = pd.read_csv(DATA_DIR / "future_forecasts.csv")
    safety_stock = pd.read_csv(DATA_DIR / "safety_stock.csv")

    history["date"] = pd.to_datetime(history["date"])
    forecasts["date"] = pd.to_datetime(forecasts["date"])

    history["sales"] = pd.to_numeric(history["sales"])
    forecasts["forecast_demand"] = pd.to_numeric(
        forecasts["forecast_demand"]
    )

    return history, forecasts, safety_stock


try:
    history, forecasts, safety_stock = load_data()
except (FileNotFoundError, pd.errors.EmptyDataError) as error:
    st.error(
        "Dashboard data is missing. Run the export cell in "
        "09_inventory_optimization.ipynb first."
    )
    st.exception(error)
    st.stop()



st.title("📦 Demand Forecasting & Inventory Optimization")

st.write(
    "Explore retail demand forecasts and translate them into "
    "inventory replenishment recommendations."
)

last_history_date = history["date"].max()

st.info(
    f"Demo dataset: historical sales end on "
    f"{last_history_date:%d %b %Y}. Forecasts cover the next "
    "14 days after that date, not live demand in 2026. "
    "Inventory inputs are illustrative and can be changed below."
)




st.sidebar.header("Dashboard Controls")

products = sorted(history["item_id"].unique().tolist())

selected_item = st.sidebar.selectbox(
    "Select product",
    products,
)

default_stock = {
    "HOBBIES_1_001": 10,
    "HOBBIES_1_002": 4,
    "HOBBIES_1_003": 2,
    "HOBBIES_1_004": 15,
    "HOBBIES_1_005": 8,
}

st.sidebar.subheader("Inventory inputs")

on_hand = st.sidebar.number_input(
    "On-hand units",
    min_value=0,
    value=default_stock.get(selected_item, 0),
    step=1,
)

on_order = st.sidebar.number_input(
    "Units already on order",
    min_value=0,
    value=0,
    step=1,
)

backorders = st.sidebar.number_input(
    "Backordered units",
    min_value=0,
    value=0,
    step=1,
)


lead_time_days = 7
review_period_days = 7
protection_days = lead_time_days + review_period_days




product_history = (
    history[history["item_id"] == selected_item]
    .sort_values("date")
    .tail(90)
)

product_forecasts = (
    forecasts[forecasts["item_id"] == selected_item]
    .sort_values("date")
    .copy()
)

safety_row = safety_stock[
    safety_stock["item_id"] == selected_item
]

if product_forecasts.empty or safety_row.empty:
    st.error("Forecast or safety-stock data is unavailable for this product.")
    st.stop()

if len(product_forecasts) < protection_days:
    st.error("Insufficient forecast days for the inventory policy.")
    st.stop()

safety_row = safety_row.iloc[0]

lead_time_safety_stock = max(
    0.0,
    float(safety_row["lead_time_safety_stock"]),
)

protection_safety_stock = max(
    0.0,
    float(safety_row["protection_safety_stock"]),
)




inventory_position = on_hand + on_order - backorders

lead_time_demand = float(
    product_forecasts.head(lead_time_days)["forecast_demand"].sum()
)

protection_period_demand = float(
    product_forecasts.head(protection_days)["forecast_demand"].sum()
)

reorder_point = lead_time_demand + lead_time_safety_stock

target_stock_level = (
    protection_period_demand + protection_safety_stock
)

recommended_order_qty = int(
    np.ceil(
        max(0.0, target_stock_level - inventory_position)
    )
)




st.subheader(f"Product overview: {selected_item}")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Forecast demand · 14 days",
    f"{protection_period_demand:.1f} units",
)

col2.metric(
    "Inventory position",
    f"{inventory_position} units",
)

col3.metric(
    "Reorder point",
    f"{reorder_point:.1f} units",
)

col4.metric(
    "Recommended order",
    f"{recommended_order_qty} units",
)




st.subheader("Inventory recommendation")

if inventory_position <= reorder_point:
    st.warning(
        "Inventory position is at or below the reorder point."
    )
elif recommended_order_qty > 0:
    st.info(
        "Inventory is above the reorder point, but the periodic-review "
        "policy recommends an order to reach the target stock level."
    )
else:
    st.success(
        "No replenishment is required under the current inventory policy."
    )

summary_col1, summary_col2 = st.columns(2)

with summary_col1:
    st.write(f"**Lead-time demand:** {lead_time_demand:.2f} units")
    st.write(
        f"**Lead-time safety stock:** "
        f"{lead_time_safety_stock:.2f} units"
    )
    st.write(f"**Reorder point:** {reorder_point:.2f} units")

with summary_col2:
    st.write(
        f"**Demand over {protection_days} days:** "
        f"{protection_period_demand:.2f} units"
    )
    st.write(
        f"**Protection-period safety stock:** "
        f"{protection_safety_stock:.2f} units"
    )
    st.write(f"**Target stock level:** {target_stock_level:.2f} units")

st.caption(
    "Inventory position = on-hand + on-order − backorders. "
    "The recommended order raises inventory position toward the "
    "target stock level. Quantities assume no additional constraints "
    "such as minimum order sizes, pack sizes, or warehouse capacity."
)



st.subheader("Historical demand and forecast")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=product_history["date"],
        y=product_history["sales"],
        mode="lines",
        name="Historical sales",
        line=dict(width=2),
    )
)

fig.add_trace(
    go.Scatter(
        x=product_forecasts["date"],
        y=product_forecasts["forecast_demand"],
        mode="lines+markers",
        name="Forecast demand",
        line=dict(dash="dash", width=2),
    )
)

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Units sold",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=20, r=20, t=50, b=20),
)

st.plotly_chart(fig, use_container_width=True)




st.subheader("14-day demand forecast")

forecast_table = product_forecasts[
    ["date", "forecast_demand"]
].copy()

forecast_table["forecast_demand"] = (
    forecast_table["forecast_demand"].round(2)
)

forecast_table = forecast_table.rename(
    columns={
        "date": "Date",
        "forecast_demand": "Forecast demand (units)",
    }
)

st.dataframe(
    forecast_table,
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    label="Download product forecast CSV",
    data=forecast_table.to_csv(index=False).encode("utf-8"),
    file_name=f"{selected_item}_forecast.csv",
    mime="text/csv",
)




with st.expander("How are these inventory recommendations calculated?"):
    st.markdown(
        """
        **Reorder point**

        Expected demand over the supplier lead time plus estimated
        lead-time safety stock.

        **Target stock level**

        Forecast demand over the lead time plus the review period,
        plus the estimated protection-period safety stock.

        **Recommended order quantity**

        The target stock level minus inventory position, rounded up
        to a whole unit and never allowed to become negative.

        Safety-stock estimates are historical approximations, not
        guaranteed service-level outcomes. Lead time and review period
        are fixed at seven days each in this first dashboard version.
        """
    )
