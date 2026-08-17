# AdaptiveXSC Production Deployment

This application is ready for production evaluation with multiple external evaluators.

## Prerequisites

1. Python 3.9+
2. Waitress WSGI server (installed via `requirements.txt`)

## Environment Variables

- `PORT` (Optional): The port on which the dashboard will run. Defaults to `8050` if not set.

*Note: No sensitive credentials or secrets are required for this deployment as the SQLite database is local and models/data are read-only.*

## Deployment Steps

1. **Activate the Environment**
   Ensure you are in the correct virtual environment.
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**
   Install the strict dependency tree.
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run Health Check**
   Verify the read-only dataset, frozen model, and database connection are intact before starting the server.
   ```powershell
   python healthcheck.py
   ```
   *Expected Output: "Healthcheck PASSED. System is ready for deployment."*

4. **Start the Production Server**
   Run the application using Waitress WSGI. This disables Dash debug mode and provides a multi-thread safe environment.
   ```powershell
   python wsgi.py
   ```
   Or optionally with a custom port:
   ```powershell
   $env:PORT="8080"; python wsgi.py
   ```

## Security & Concurrency Features

- **No Developer Mode**: The `debug=True` mode, which exposes Python traceback consoles and arbitrary code execution vulnerabilities, is inherently disabled when running via `wsgi.py`.
- **Database Atomicity**: Concurrent external evaluators can submit decisions and feedback simultaneously. SQLite transactional locking prevents file corruption.
- **Session Isolation**: User-specific variables (selected dates, SKUs, and scenarios) are strictly maintained inside the browser's DOM (`dcc.Store`) and evaluated functionally in Python, guaranteeing no leakage between Evaluator A and Evaluator B.
