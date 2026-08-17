class DecisionEngine:
    def __init__(self, high_demand_multiplier: float = 1.5):
        """
        Initialize the Decision Engine.
        Args:
            high_demand_multiplier: Configurable high-demand decision threshold.
        """
        self.high_demand_multiplier = high_demand_multiplier

    def evaluate(self, forecast: float, inventory_level: float, reorder_point: float, order_quantity: float, recent_demand: float = None) -> dict:
        """
        Evaluate the operational state and return a structured decision recommendation.
        """
        if forecast < 0 or inventory_level < 0 or reorder_point < 0 or order_quantity < 0:
            raise ValueError("Negative inputs are not allowed.")

        rules = []
        severity = "LOW"
        decision_state = "NORMAL"
        explanation = ""

        is_high_demand = False
        if recent_demand is not None and recent_demand > 0:
            # Triggered if forecast >= recent_demand * high_demand_multiplier
            if forecast >= (recent_demand * self.high_demand_multiplier):
                is_high_demand = True

        if is_high_demand:
            decision_state = "HIGH_DEMAND_ALERT"
            severity = "HIGH"
            rules.append("forecast_substantially_above_recent_demand")
            explanation = "Forecast demand is substantially above the recent demand baseline."

        if inventory_level <= reorder_point:
            rules.append("inventory_below_reorder_point")
            if is_high_demand:
                severity = "HIGH"
                explanation = "Inventory is below the configured reorder point while forecast demand remains elevated."
            else:
                decision_state = "REVIEW_REPLENISHMENT"
                severity = "MEDIUM"
                explanation = "Inventory is at or below the configured reorder point."
                
        if decision_state == "NORMAL":
            explanation = "Inventory is comfortably above the reorder point and forecast does not indicate immediate pressure."
            
        return {
            "decision_state": decision_state,
            "severity": severity,
            "forecast": forecast,
            "inventory_level": inventory_level,
            "reorder_point": reorder_point,
            "order_quantity": order_quantity,
            "triggered_rules": rules,
            "explanation": explanation
        }

    def evaluate_scenario_comparison(self, baseline_eval: dict, scenario_eval: dict) -> dict:
        """
        Compare baseline and scenario evaluations to determine escalation risk.
        """
        # Deep copy to avoid mutating the original dicts passed in
        import copy
        base_eval = copy.deepcopy(baseline_eval)
        scen_eval = copy.deepcopy(scenario_eval)
        
        severity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        
        base_sev = severity_rank.get(base_eval["severity"], 0)
        scen_sev = severity_rank.get(scen_eval["severity"], 0)
        
        if scen_sev > base_sev or (base_eval["decision_state"] == "NORMAL" and scen_eval["decision_state"] != "NORMAL"):
            scen_eval["decision_state"] = "SCENARIO_RISK"
            scen_eval["severity"] = "CRITICAL"
            scen_eval["triggered_rules"].append("scenario_escalates_severity")
            scen_eval["explanation"] += " A selected what-if scenario causes the decision state to become more severe."
            
        return {
            "baseline_decision": base_eval,
            "scenario_decision": scen_eval,
            "forecast_change": scen_eval["forecast"] - base_eval["forecast"],
            "decision_change": f"{base_eval['decision_state']} -> {scen_eval['decision_state']}",
            "triggered_rules": scen_eval["triggered_rules"]
        }
