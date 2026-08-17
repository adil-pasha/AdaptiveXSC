import unittest
import pandas as pd
import numpy as np
import xgboost as xgb
from src.sim.simulator import WhatIfSimulator

class TestWhatIfSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features = [
            'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold',
            'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity',
            'Unit_Cost', 'Unit_Price', 'Promotion_Flag'
        ]
        
        # Train a dummy model
        np.random.seed(42)
        X = pd.DataFrame(np.random.rand(100, 8) * 10, columns=cls.features)
        X['Promotion_Flag'] = np.random.randint(0, 2, 100)
        y = np.random.rand(100) * 20
        
        cls.model = xgb.XGBRegressor(n_estimators=10, max_depth=3, random_state=42)
        cls.model.fit(X, y)
        cls.sim = WhatIfSimulator(cls.model)
        
        cls.baseline = pd.DataFrame([{
            'Lag_1_Units_Sold': 10.0,
            'Lag_7_Units_Sold': 12.0,
            'Rolling_7d_Mean_Units_Sold': 11.0,
            'Lag_1_Inventory_Level': 50.0,
            'Lag_1_Order_Quantity': 20.0,
            'Unit_Cost': 5.0,
            'Unit_Price': 10.0,
            'Promotion_Flag': 0.0
        }])

    def test_no_change_scenario(self):
        res = self.sim.simulate(self.baseline, {})
        self.assertAlmostEqual(res['baseline_forecast'], res['scenario_forecast'])
        self.assertAlmostEqual(res['forecast_difference'], 0)

    def test_promotion_toggle(self):
        res = self.sim.simulate(self.baseline, {'Promotion_Flag': 1})
        self.assertEqual(res['scenario_features']['Promotion_Flag'], 1.0)

    def test_price_perturbation_valid(self):
        res = self.sim.simulate(self.baseline, {'Unit_Price': 8.5})
        self.assertEqual(res['scenario_features']['Unit_Price'], 8.5)
        
    def test_invalid_ranges(self):
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Unit_Price': -5})
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Promotion_Flag': 2})

    def test_target_protection(self):
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Units_Sold': 50})

    def test_excluded_feature_protection(self):
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Demand_Forecast': 50})
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Stockout_Flag': 1})
        with self.assertRaises(ValueError):
            self.sim.simulate(self.baseline, {'Month': 10})

    def test_shap_consistency(self):
        res = self.sim.simulate(self.baseline, {'Lag_1_Units_Sold': 20})
        self.assertTrue(res['baseline_shap']['reconstruction_verified'])
        self.assertTrue(res['scenario_shap']['reconstruction_verified'])

    def test_determinism(self):
        res1 = self.sim.simulate(self.baseline, {'Unit_Price': 12.0})
        res2 = self.sim.simulate(self.baseline, {'Unit_Price': 12.0})
        self.assertEqual(res1['scenario_forecast'], res2['scenario_forecast'])
        self.assertEqual(res1['forecast_difference'], res2['forecast_difference'])

if __name__ == '__main__':
    unittest.main()
