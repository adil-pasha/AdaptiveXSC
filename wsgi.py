import os
from waitress import serve
from src.app.app import app

if __name__ == '__main__':
    # Get port from environment variable, default to 8050
    port = int(os.environ.get('PORT', 8050))
    
    # Waitress binds to 0.0.0.0 by default when using host='0.0.0.0', 
    # but we can specify it explicitly.
    # Disabling debug mode is handled by not calling app.run(debug=True)
    
    print(f"Starting production Waitress server on 0.0.0.0:{port}...")
    serve(app.server, host='0.0.0.0', port=port, _quiet=False)
