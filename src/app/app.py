import os
import sys

# Ensure src is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dash import Dash
import dash_bootstrap_components as dbc
from src.app.layout import create_layout
from src.app.callbacks import register_callbacks

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "AdaptiveXSC Decision Intelligence"

app.layout = create_layout
register_callbacks(app)

if __name__ == '__main__':
    app.run(debug=True, port=8050)
