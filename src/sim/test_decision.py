import unittest
from src.sim.decision import DecisionEngine

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_normal_state(self):
        # 1. Inventory above reorder point -> NORMAL
        res = self.engine.evaluate(forecast=10, inventory_level=100, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res["decision_state"], "NORMAL")
        self.assertEqual(len(res["triggered_rules"]), 0)

    def test_review_replenishment(self):
        # 2. Inventory below reorder point -> REVIEW_REPLENISHMENT
        res = self.engine.evaluate(forecast=10, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res["decision_state"], "REVIEW_REPLENISHMENT")
        self.assertIn("inventory_below_reorder_point", res["triggered_rules"])

    def test_high_demand_alert(self):
        # 3. High forecast condition -> HIGH_DEMAND_ALERT
        # forecast 30 > 10 * 1.5
        res = self.engine.evaluate(forecast=30, inventory_level=100, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res["decision_state"], "HIGH_DEMAND_ALERT")
        self.assertIn("forecast_substantially_above_recent_demand", res["triggered_rules"])

    def test_scenario_risk(self):
        # 4. Scenario causing escalation -> SCENARIO_RISK
        base = self.engine.evaluate(forecast=10, inventory_level=100, reorder_point=50, order_quantity=20, recent_demand=10)
        scen = self.engine.evaluate(forecast=10, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        
        comp = self.engine.evaluate_scenario_comparison(base, scen)
        self.assertEqual(comp["scenario_decision"]["decision_state"], "SCENARIO_RISK")
        self.assertIn("scenario_escalates_severity", comp["scenario_decision"]["triggered_rules"])

    def test_boundary_conditions(self):
        # 5. Boundary conditions (exactly at reorder point, exactly at threshold multiplier)
        res1 = self.engine.evaluate(forecast=10, inventory_level=50, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res1["decision_state"], "REVIEW_REPLENISHMENT")
        
        # Exact boundary: forecast (15) == recent_demand (10) * multiplier (1.5)
        res2 = self.engine.evaluate(forecast=15, inventory_level=100, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res2["decision_state"], "HIGH_DEMAND_ALERT")
        
        # Just below boundary: forecast (14.9) < recent_demand (10) * multiplier (1.5)
        res3 = self.engine.evaluate(forecast=14.9, inventory_level=100, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res3["decision_state"], "NORMAL")

    def test_missing_inputs(self):
        # 6. Missing required inputs
        with self.assertRaises(TypeError):
            self.engine.evaluate(forecast=10, inventory_level=100) # missing reorder_point, order_quantity

    def test_invalid_negative_values(self):
        # 7. Invalid negative values
        with self.assertRaises(ValueError):
            self.engine.evaluate(forecast=-5, inventory_level=100, reorder_point=50, order_quantity=20)
        with self.assertRaises(ValueError):
            self.engine.evaluate(forecast=10, inventory_level=-10, reorder_point=50, order_quantity=20)

    def test_determinism(self):
        # 8. Deterministic identical inputs -> identical recommendation
        res1 = self.engine.evaluate(forecast=30, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        res2 = self.engine.evaluate(forecast=30, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res1, res2)

    def test_rule_traceability(self):
        # 9. Rule traceability: every non-normal decision has at least one triggered rule
        res = self.engine.evaluate(forecast=10, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertNotEqual(res["decision_state"], "NORMAL")
        self.assertGreater(len(res["triggered_rules"]), 0)

    def test_no_fabricated_order_quantity(self):
        # 10. No fabricated order quantity recommendation
        res = self.engine.evaluate(forecast=10, inventory_level=40, reorder_point=50, order_quantity=20, recent_demand=10)
        self.assertEqual(res["order_quantity"], 20) # Must match input exactly

if __name__ == '__main__':
    unittest.main()
