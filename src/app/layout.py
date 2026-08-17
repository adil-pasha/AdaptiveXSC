from dash import html, dcc
import dash_bootstrap_components as dbc
from src.models.loader import DataLoader

def create_layout():
    # Load dataset to populate dropdowns
    _, df_test = DataLoader.load()
    
    # Get unique IDs for dropdowns
    sku_options = [{'label': s, 'value': s} for s in df_test['SKU_ID'].unique()]
    wh_options = [{'label': w, 'value': w} for s in df_test['Warehouse_ID'].unique() for w in [s]] # unique hack
    wh_options = [{'label': w, 'value': w} for w in df_test['Warehouse_ID'].unique()]
    
    # Get a valid default
    default_idx = df_test.index[0]
    default_sku = df_test.loc[default_idx, 'SKU_ID']
    default_wh = df_test.loc[default_idx, 'Warehouse_ID']

    return dbc.Container([
        dbc.Row([
            dbc.Col(html.H2("AdaptiveXSC Decision Intelligence", className="mt-4 mb-4"), xs=12, md=12)
        ]),
        
        # ONBOARDING SECTION
        dbc.Row([
            dbc.Col(
                dbc.Accordion([
                    dbc.AccordionItem([
                        html.P(html.Strong("What is AdaptiveXSC?")),
                        html.P("AdaptiveXSC is a decision-support system for supply-chain demand forecasting. It provides a model forecast, explains the main factors behind that forecast, and lets you explore hypothetical scenarios."),
                        html.P(html.Strong("What does the forecast mean?")),
                        html.P("The forecast is the model's estimated demand for the selected SKU, warehouse, and date."),
                        html.P(html.Strong("What does SHAP mean?")),
                        html.P("SHAP shows which model inputs pushed this particular forecast higher or lower. These are model explanations, not causal claims."),
                        html.P(html.Strong("What does What-If mean?")),
                        html.P("What-If lets you change selected inputs and observe how the model's forecast and rule-based decision respond. It is a model simulation, not a guarantee of real-world outcomes."),
                        html.P(html.Strong("Human Decision Options:")),
                        html.Ul([
                            html.Li([html.Strong("ACCEPT: "), "I agree with the system's decision for this observation."]),
                            html.Li([html.Strong("REJECT: "), "I do not agree with the system's decision."]),
                            html.Li([html.Strong("OVERRIDE: "), "I want to replace the system's decision with my own judgment. (Requires a reason)"])
                        ])
                    ], title="Welcome to AdaptiveXSC - Click here for instructions")
                ], start_collapsed=True, className="mb-4"),
                xs=12, md=12
            )
        ]),

        # EVALUATOR IDENTIFICATION SECTION
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col(html.Label("Evaluator ID:", className="fw-bold mt-1"), xs=12, md="auto"),
                        dbc.Col(
                            dbc.Input(
                                id="evaluator-id-input", 
                                type="text", 
                                placeholder="Enter your evaluator code (e.g. EVAL-001)",
                                maxLength=50
                            ),
                            xs=12, md=6
                        ),
                        dbc.Col(
                            html.Div(id="evaluator-id-display", className="fw-bold text-primary mt-1"),
                            xs=12, md="auto"
                        )
                    ])
                ])
            ], className="mb-4 shadow-sm border-primary"), xs=12, md=12)
        ]),
        
        # Data Collection Monitor & Filters
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Data Collection Monitor"),
                dbc.CardBody(id="collection-monitor-content", children=[
                    html.P("Loading statistics...")
                ])
            ], className="mb-4 shadow-sm"), xs=12, md=4),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader("Diversity Filter"),
                dbc.CardBody([
                    dbc.Label("Promotion Filter:"),
                    dcc.Dropdown(
                        id="filter-promo",
                        options=[
                            {"label": "Any", "value": "any"},
                            {"label": "Promotion Active (1)", "value": 1},
                            {"label": "Promotion Inactive (0)", "value": 0}
                        ],
                        value="any",
                        clearable=False,
                        className="mb-2"
                    ),
                    html.Small("Use filters to explore diverse observations.", className="text-muted")
                ])
            ], className="mb-4 shadow-sm"), xs=12, md=8)
        ]),
        
        # TOP CONTROL PANEL
        dbc.Card([
            dbc.CardHeader(html.H5("Observation Selection & Scenario Controls", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Warehouse:"),
                        dcc.Dropdown(id='warehouse-dropdown', options=wh_options, value=default_wh, clearable=False),
                    ], xs=12, md=4),
                    dbc.Col([
                        html.Label("SKU:"),
                        dcc.Dropdown(id='sku-dropdown', options=sku_options, value=default_sku, clearable=False),
                    ], xs=12, md=4),
                    dbc.Col([
                        html.Label("Date:"),
                        dcc.Dropdown(id='date-dropdown', clearable=False),
                    ], xs=12, md=4),
                ], className="mb-3"),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        html.Label("Scenario: Promotion Toggle"),
                        dcc.RadioItems(
                            id='scenario-promo',
                            options=[{'label': ' Baseline (No Change)', 'value': 'base'}, 
                                     {'label': ' Force Active (1)', 'value': 1},
                                     {'label': ' Force Inactive (0)', 'value': 0}],
                            value='base',
                            labelStyle={'display': 'block'}
                        )
                    ], xs=12, md=3),
                    dbc.Col([
                        html.Label("Scenario: Unit Price % Change"),
                        dcc.Slider(id='scenario-price-pct', min=-50, max=50, step=5, value=0,
                                   marks={i: f"{i}%" for i in range(-50, 51, 25)})
                    ], xs=12, md=3),
                    dbc.Col([
                        html.Label("Scenario: Unit Cost % Change"),
                        dcc.Slider(id='scenario-cost-pct', min=-50, max=50, step=5, value=0,
                                   marks={i: f"{i}%" for i in range(-50, 51, 25)})
                    ], xs=12, md=3),
                    dbc.Col([
                        html.Label("Scenario: Lag_1_Inventory % Change"),
                        dcc.Slider(id='scenario-inv-pct', min=-50, max=50, step=5, value=0,
                                   marks={i: f"{i}%" for i in range(-50, 51, 25)})
                    ], xs=12, md=3),
                ])
            ])
        ], className="mb-4 shadow-sm"),

        # SECTION 1: FORECAST KPI
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Baseline State", className="mb-0")),
                dbc.CardBody(id="baseline-kpi-content")
            ], className="h-100 shadow-sm"), xs=12, md=12)
        ], className="mb-4"),

        # SECTION 2: SHAP EXPLANATION
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Forecast Drivers (SHAP Explanation)", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="shap-explanation-text", className="mb-3 font-italic text-muted"),
                    dcc.Graph(id="shap-bar-chart")
                ])
            ], className="h-100 shadow-sm"), xs=12, md=12)
        ], className="mb-4"),

        # SECTION 3 & 4: SCENARIO & DECISION
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("What-If Scenario Analysis", className="mb-0")),
                dbc.CardBody(id="scenario-kpi-content")
            ], className="h-100 shadow-sm"), xs=12, md=6),
            
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Decision Explanation", className="mb-0")),
                dbc.CardBody(id="decision-explanation-content")
            ], className="h-100 shadow-sm"), xs=12, md=6)
        ], className="mb-4"),

        # SECTION 5: HUMAN DECISION
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("HUMAN DECISION", className="mb-0")),
                dbc.CardBody([
                    html.Div(id="human-decision-summary", className="mb-3"),
                    
                    html.Div([
                        dbc.Button("ACCEPT", id="btn-accept", color="success", className="me-2", n_clicks=0),
                        dbc.Button("REJECT", id="btn-reject", color="danger", className="me-2", n_clicks=0),
                        dbc.Button("OVERRIDE", id="btn-override", color="warning", n_clicks=0),
                    ], className="mb-3"),
                    
                    dbc.Tooltip("I agree with the system's decision.", target="btn-accept"),
                    dbc.Tooltip("I do not agree with the system's decision.", target="btn-reject"),
                    dbc.Tooltip("I want to replace the system's decision with my own judgment.", target="btn-override"),
                    
                    html.Div(id="override-panel", style={"display": "none"}, children=[
                        dbc.Label("Reason:"),
                        dbc.Select(
                            id="override-reason",
                            options=[
                                {"label": r, "value": r} for r in [
                                    "Supplier Delay", "Upcoming Promotion", "Local Demand Knowledge",
                                    "Inventory Constraint", "Data Quality Concern", 
                                    "Forecast Appears Too High", "Forecast Appears Too Low", "Other"
                                ]
                            ],
                            value=None,
                            className="mb-2"
                        ),
                        dbc.Label("Additional note:"),
                        dbc.Textarea(id="override-note", className="mb-3"),
                    ]),
                    
                    dbc.Button("SUBMIT DECISION", id="btn-submit", color="primary", className="mb-3", n_clicks=0),
                    html.Div(id="submit-message")
                ])
            ], className="mb-4 shadow-sm"), xs=12, md=12)
        ]),

        # SECTION 6: EVALUATOR FEEDBACK
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5("Evaluator Feedback", className="mb-0 text-white"), className="bg-secondary"),
                dbc.CardBody([
                    dbc.Label("Feedback Type:"),
                    dbc.Select(
                        id="feedback-type",
                        options=[{"label": r, "value": r} for r in ["Bug", "Confusing Explanation", "UI Problem", "Other"]],
                        value=None,
                        className="mb-2"
                    ),
                    dbc.Label("Description:"),
                    dbc.Textarea(id="feedback-text", className="mb-3", maxLength=2000),
                    dbc.Button("Submit Feedback", id="btn-submit-feedback", color="secondary", n_clicks=0),
                    html.Div(id="feedback-message", className="mt-2")
                ])
            ], className="mb-4 shadow-sm border-secondary"), xs=12, md=12)
        ]),

        # Store hidden states
        dcc.Store(id="selected-action-store", data=None),
        dcc.Store(id="system-state-store", data=None),
        dcc.Store(id="last-submitted-fingerprint", data=None)

    ], fluid=True, className="p-4")
