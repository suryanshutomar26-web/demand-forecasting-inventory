
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Support running Streamlit from either the project root
# or the app directory.
try:
    from inventory import calculate_inventory_metrics
except ModuleNotFoundError:
    from app.inventory import calculate_inventory_metrics


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Demand Forecasting & Inventory Optimization",
    page_icon="📦",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

LEAD_TIME_DAYS = 7
REVIEW_PERIOD_DAYS = 7
PROTECTION_DAYS = LEAD_TIME_DAYS + REVIEW_PERIOD_DAYS


# --------------------------------------------------
# 2. Load the exported demo data
# --------------------------------------------------

@st.cache_data
def load_data():
    history = pd.read_csv(DATA_DIR / "historical_sales.csv")
    forecasts = pd.read_csv(DATA_DIR / "future_forecasts.csv")
    safety = pd.read_csv(DATA_DIR / "safety_stock.csv")

    required_history = {"date", "item_id", "store_id", "sales"}
    required_forecasts = {
        "date", "item_id", "store_id", "forecast_demand"
    }
    required_safety = {
        "item_id",
        "lead_time_safety_stock",
        "protection_safety_stock",
    }

    if not required_history.issubset(history.columns):
        raise ValueError("Historical sales file has missing columns.")

    if not required_forecasts.issubset(forecasts.columns):
        raise ValueError("Forecast file has missing columns.")

    if not required_safety.issubset(safety.columns):
        raise ValueError("Safety-stock file has missing columns.")

    history["date"] = pd.to_datetime(history["date"], errors="raise")
    forecasts["date"] = pd.to_datetime(forecasts["date"], errors="raise")

    history["sales"] = pd.to_numeric(
        history["sales"], errors="raise"
    )
    forecasts["forecast_demand"] = pd.to_numeric(
        forecasts["forecast_demand"], errors="raise"
    )

    if (
        not np.isfinite(history["sales"]).all()
        or (history["sales"] < 0).any()
    ):
        raise ValueError("Historical sales contain invalid values.")

    if (
        not np.isfinite(forecasts["forecast_demand"]).all()
        or (forecasts["forecast_demand"] < 0).any()
    ):
        raise ValueError("Forecast data contains invalid values.")

    return history, forecasts, safety


try:
    history, forecasts, safety = load_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not load dashboard data: {error}")
    st.stop()


# --------------------------------------------------
# 3. Header
# --------------------------------------------------

st.title("📦 Demand Forecasting & Inventory Optimization")

st.write(
    "Forecast retail demand and translate forecasts into "
    "inventory replenishment recommendations."
)

last_history_date = history["date"].max()

st.info(
    f"This demonstration uses historical M5 data ending "
    f"{last_history_date:%d %B %Y}. Forecasts are based on this "
    "historical dataset, not live retail demand. Inventory levels "
    "are illustrative."
)


# --------------------------------------------------
# 4. Sidebar controls
# --------------------------------------------------

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
    key=f"on_hand_{selected_item}",
)

on_order = st.sidebar.number_input(
    "Units already on order",
    min_value=0,
    value=0,
    step=1,
    key=f"on_order_{selected_item}",
)

backorders = st.sidebar.number_input(
    "Backordered units",
    min_value=0,
    value=0,
    step=1,
    key=f"backorders_{selected_item}",
)


# --------------------------------------------------
# 5. Select data for the chosen product
# --------------------------------------------------

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

safety_row = safety[safety["item_id"] == selected_item]

if product_history.empty:
    st.error("Historical data is unavailable for this product.")
    st.stop()

if product_forecasts.empty or safety_row.empty:
    st.error("Forecast or safety-stock data is unavailable.")
    st.stop()

if len(product_forecasts) < PROTECTION_DAYS:
    st.error(
        f"At least {PROTECTION_DAYS} forecast days are needed "
        "for the current inventory policy."
    )
    st.stop()

safety_row = safety_row.iloc[0]

lead_time_safety_stock = max(
    0.0,
    float(safety_row["lead_time_safety_stock"]),
)

protection_period_safety_stock = max(
    0.0,
    float(safety_row["protection_safety_stock"]),
)


# --------------------------------------------------
# 6. Forecast demand over the required periods
# --------------------------------------------------

lead_time_demand = float(
    product_forecasts.head(LEAD_TIME_DAYS)["forecast_demand"].sum()
)

protection_period_demand = float(
    product_forecasts.head(PROTECTION_DAYS)["forecast_demand"].sum()
)


# --------------------------------------------------
# 7. Use the tested inventory calculation function
# --------------------------------------------------

inventory_metrics = calculate_inventory_metrics(
    on_hand_units=on_hand,
    on_order_units=on_order,
    backorders=backorders,
    lead_time_demand=lead_time_demand,
    protection_period_demand=protection_period_demand,
    lead_time_safety_stock=lead_time_safety_stock,
    protection_period_safety_stock=protection_period_safety_stock,
)

inventory_position = inventory_metrics["inventory_position"]
reorder_point = inventory_metrics["reorder_point"]
target_stock_level = inventory_metrics["target_stock_level"]
recommended_order_qty = inventory_metrics["recommended_order_qty"]
below_reorder_point = inventory_metrics["below_reorder_point"]
reorder_status = inventory_metrics["reorder_status"]


# --------------------------------------------------
# 8. Inventory KPIs
# --------------------------------------------------

st.subheader(f"Product overview: {selected_item}")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "14-day forecast",
    f"{protection_period_demand:.1f} units",
)

col2.metric(
    "Inventory position",
    f"{inventory_position:.1f} units",
)

col3.metric(
    "Reorder point",
    f"{reorder_point:.1f} units",
)

col4.metric(
    "Recommended order",
    f"{recommended_order_qty} units",
)


# --------------------------------------------------
# 9. Replenishment recommendation
# --------------------------------------------------

st.subheader("Inventory recommendation")

if below_reorder_point:
    st.warning(
        "Inventory position is at or below the reorder point."
    )
elif recommended_order_qty > 0:
    st.info(
        "An order is recommended to reach the target stock level, "
        "even though inventory is above the reorder point."
    )
else:
    st.success(
        "No replenishment is required under the current inventory policy."
    )

left, right = st.columns(2)

with left:
    st.write(f"**Status:** {reorder_status}")
    st.write(f"**Lead-time demand:** {lead_time_demand:.2f} units")
    st.write(
        f"**Lead-time safety stock:** "
        f"{lead_time_safety_stock:.2f} units"
    )
    st.write(f"**Reorder point:** {reorder_point:.2f} units")

with right:
    st.write(
        f"**Protection-period demand:** "
        f"{protection_period_demand:.2f} units"
    )
    st.write(
        f"**Protection-period safety stock:** "
        f"{protection_period_safety_stock:.2f} units"
    )
    st.write(f"**Target stock level:** {target_stock_level:.2f} units")
    st.write(
        f"**Inventory position:** {inventory_position:.2f} units"
    )

st.caption(
    "Inventory position = on-hand + on-order − backorders. "
    "The policy assumes a 7-day supplier lead time and a 7-day "
    "review period. Safety-stock estimates are preliminary and "
    "are not guaranteed service-level outcomes."
)


# --------------------------------------------------
# 10. Historical sales and demand forecast chart
# --------------------------------------------------

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


# --------------------------------------------------
# 11. Forecast table and CSV download
# --------------------------------------------------

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


# --------------------------------------------------
# 12. Explain how the inventory policy works
# --------------------------------------------------

with st.expander("How are inventory recommendations calculated?"):
    st.markdown(
        """
        **Reorder point**

        Expected demand over the supplier lead time plus lead-time
        safety stock.

        **Target stock level**

        Expected demand over the lead time plus review period,
        plus protection-period safety stock.

        **Recommended order quantity**

        The non-negative difference between target stock level and
        inventory position, rounded up to a whole unit.

        **Limitations**

        The current prototype uses illustrative inventory levels,
        fixed lead and review periods, and preliminary safety-stock
        estimates. It does not optimize purchase cost, minimum order
        quantities, pack sizes, warehouse capacity, or changing
        supplier lead times.
        """
    )
