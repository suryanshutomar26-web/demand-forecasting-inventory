import unittest

from app.inventory import calculate_inventory_metrics


class TestInventoryMetrics(unittest.TestCase):

    def calculate(self, **overrides):
        inputs = {
            "on_hand_units": 3,
            "on_order_units": 0,
            "backorders": 0,
            "lead_time_demand": 5,
            "protection_period_demand": 10,
            "lead_time_safety_stock": 2,
            "protection_period_safety_stock": 3,
        }
        inputs.update(overrides)
        return calculate_inventory_metrics(**inputs)

    def test_below_reorder_point(self):
        result = self.calculate()

        self.assertEqual(result["inventory_position"], 3)
        self.assertEqual(result["reorder_point"], 7)
        self.assertEqual(result["target_stock_level"], 13)
        self.assertEqual(result["recommended_order_qty"], 10)
        self.assertTrue(result["below_reorder_point"])

    def test_order_above_reorder_point_below_target(self):
        result = self.calculate(on_hand_units=10)

        self.assertFalse(result["below_reorder_point"])
        self.assertEqual(result["recommended_order_qty"], 3)
        self.assertEqual(result["reorder_status"], "Order to target")

    def test_no_order_at_target(self):
        result = self.calculate(on_hand_units=13)

        self.assertEqual(result["recommended_order_qty"], 0)
        self.assertEqual(result["reorder_status"], "No order needed")

    def test_negative_inventory_rejected(self):
        with self.assertRaises(ValueError):
            self.calculate(on_hand_units=-1)

    def test_nan_demand_rejected(self):
        with self.assertRaises(ValueError):
            self.calculate(lead_time_demand=float("nan"))


if __name__ == "__main__":
    unittest.main()