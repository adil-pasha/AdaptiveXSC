from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, timezone
import uuid
import json

class AuditRecord(BaseModel):
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Context
    SKU_ID: str
    Warehouse_ID: str
    Date: str
    
    # Original System State
    baseline_forecast: float
    actual_units_sold: Optional[float] = None
    inventory_level: float
    reorder_point: float
    baseline_decision_state: str
    baseline_severity: str
    
    # Scenario System State
    scenario_applied: bool
    scenario_description: str
    scenario_forecast: float
    scenario_decision_state: str
    scenario_severity: str
    
    # Explainability (Structured serialized string)
    top_shap_drivers: str 
    
    # Human Action
    evaluator_id: Optional[str] = None
    manager_action: str
    override_reason: Optional[str] = None
    override_note: Optional[str] = None
    
    @validator('evaluator_id')
    def validate_evaluator_id(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 50:
                raise ValueError("evaluator_id exceeds maximum length of 50")
            if len(v) == 0:
                raise ValueError("evaluator_id cannot be empty whitespace")
        return v
        
    @validator('manager_action')
    def validate_action(cls, v):
        allowed = {'ACCEPT', 'REJECT', 'OVERRIDE'}
        if v not in allowed:
            raise ValueError(f"manager_action must be one of {allowed}")
        return v
        
    @validator('override_reason', always=True)
    def validate_override_reason(cls, v, values):
        action = values.get('manager_action')
        if action == 'OVERRIDE' and not v:
            raise ValueError("override_reason is required when manager_action is OVERRIDE")
        if action in ['ACCEPT', 'REJECT'] and v:
            pass # We don't require it, but we can allow it or drop it, let's keep it if they provide it.
        return v

    def to_csv_dict(self):
        """Returns a dict matching exactly the CSV schema order."""
        return {
            'audit_id': self.audit_id,
            'timestamp': self.timestamp,
            'SKU_ID': self.SKU_ID,
            'Warehouse_ID': self.Warehouse_ID,
            'Date': self.Date,
            'baseline_forecast': self.baseline_forecast,
            'actual_units_sold': self.actual_units_sold if self.actual_units_sold is not None else '',
            'inventory_level': self.inventory_level,
            'reorder_point': self.reorder_point,
            'baseline_decision_state': self.baseline_decision_state,
            'baseline_severity': self.baseline_severity,
            'scenario_applied': self.scenario_applied,
            'scenario_description': self.scenario_description,
            'scenario_forecast': self.scenario_forecast,
            'scenario_decision_state': self.scenario_decision_state,
            'scenario_severity': self.scenario_severity,
            'top_shap_drivers': self.top_shap_drivers,
            'evaluator_id': self.evaluator_id if self.evaluator_id is not None else '',
            'manager_action': self.manager_action,
            'override_reason': self.override_reason if self.override_reason is not None else '',
            'override_note': self.override_note if self.override_note is not None else ''
        }

    @classmethod
    def get_csv_headers(cls):
        # Must match to_csv_dict keys perfectly
        return [
            'audit_id', 'timestamp', 'SKU_ID', 'Warehouse_ID', 'Date',
            'baseline_forecast', 'actual_units_sold', 'inventory_level', 'reorder_point',
            'baseline_decision_state', 'baseline_severity',
            'scenario_applied', 'scenario_description', 'scenario_forecast',
            'scenario_decision_state', 'scenario_severity',
            'top_shap_drivers', 'evaluator_id', 'manager_action', 'override_reason', 'override_note'
        ]

class FeedbackRecord(BaseModel):
    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evaluator_id: str
    
    # Context
    SKU_ID: str
    Warehouse_ID: str
    Date: str
    baseline_decision_state: str
    scenario_description: Optional[str] = None
    
    # Feedback
    feedback_type: str
    feedback_text: str
    
    @validator('evaluator_id')
    def validate_evaluator_id(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("evaluator_id cannot be empty")
        return v
        
    @validator('feedback_type')
    def validate_type(cls, v):
        allowed = {'Bug', 'Confusing Explanation', 'UI Problem', 'Other'}
        if v not in allowed:
            raise ValueError(f"feedback_type must be one of {allowed}")
        return v
        
    @validator('feedback_text')
    def validate_text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("feedback_text cannot be empty")
        if len(v) > 2000:
            raise ValueError("feedback_text exceeds 2000 characters limit")
        return v

