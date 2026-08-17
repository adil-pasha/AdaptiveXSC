# AdaptiveXSC Project Context

## 1. Vision
AdaptiveXSC is a mid-market-accessible, explainable demand-forecasting and scenario-simulation platform. The primary research contribution is an **override/audit log** that captures *why* a manager accepts, rejects, or overrides an AI recommendation, producing a trust-calibration dataset. 

Every feature exists to serve one of two pillars:
1. **Mid-market accessibility**
2. **Trust calibration**

## 2. Locked-in Decisions
- **Forecasting model**: XGBoost (Prophet is only a baseline comparison, not the primary path).
- **Stockout/delay risk**: Logistic regression (XGBoost classifier as fallback).
- **Explainability**: SHAP + LIME (supporting infrastructure, not the headline).
- **Dashboard/UI**: Plotly Dash.
- **Infrastructure**: Local laptop (16GB RAM / 4-core) + Google Colab / Kaggle. No AWS EC2/GPU instances.

## 3. Phased Development Plan
- **Phase I — ETL & Data Foundation**: Set up local environment, ingest Kaggle dataset, build ETL pipeline, validate cleaned DataFrame.
- **Phase II — Models & Explainability (XAI)**: Train XGBoost baseline, logistic regression risk model, integrate SHAP/LIME.
- **Phase III — Dashboard, Simulator, Override Log**: Build Dash dashboard, scenario simulator, and the override/audit log.
