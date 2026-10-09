
from math import ceil, isfinite
from numbers import Real


def calculate_inventory_metrics(
    on_hand_units,
    on_order_units,
    backorders,
    lead_time_demand,
    protection_period_demand,
    lead_time_safety_stock,
    protection_period_safety_stock,
):
    """Calculate inventory position and replenishment recommendations."""

    inputs = {
        "on_hand_units": on_hand_units,
        "on_order_units": on_order_units,
        "backorders": backorders,
        "lead_time_demand": lead_time_demand,
        "protection_period_demand": protection_period_demand,
        "lead_time_safety_stock": lead_time_safety_stock,
        "protection_period_safety_stock": protection_period_safety_stock,
    }

    for name, value in inputs.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not isfinite(float(value))
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite, non-negative number."
            )

    inventory_position = (
        on_hand_units + on_order_units - backorders
    )

    reorder_point = (
        lead_time_demand + lead_time_safety_stock
    )

    target_stock_level = (
        protection_period_demand
        + protection_period_safety_stock
    )

    recommended_order_qty = int(
        ceil(max(0, target_stock_level - inventory_position))
    )

    return {
        "inventory_position": inventory_position,
        "reorder_point": reorder_point,
        "target_stock_level": target_stock_level,
        "recommended_order_qty": recommended_order_qty,
        "below_reorder_point": inventory_position <= reorder_point,
        "reorder_status": (
            "Order to target"
            if recommended_order_qty > 0
            else "No order needed"
        ),
    }
