# Alpha King

Streamlit workspace for alpha ideation, transparent local backtesting, portfolio review and user-confirmed WorldQuant BRAIN browser access.

## Windows
Run `run_windows.bat` with Python 3.10+ installed.

## Streamlit Community Cloud
Push this project to GitHub. Create a Streamlit Community Cloud app from the repository, select the branch, set `app.py` as the main file, and deploy. Dependencies are in `requirements.txt`.

## BRAIN browser access
Open the official BRAIN website, sign in there yourself, return to Alpha King and confirm login to start a four-hour local timer. The ACTIVE label is user-confirmed local state, not technical verification of the remote session. The app does not read cookies, ask for your password, or synchronize BRAIN data.

## Local simulation
Upload daily panel CSV data with `date,symbol,close` and optional numeric factor columns. Strategies include price momentum, mean reversion, factor rank and factor momentum. Daily dollar-neutral long/short positions use next-period returns and configurable one-way costs. Reports include Sharpe, annual return, drawdown, turnover, fitness, volatility, Sortino, win rate and in/out-of-sample splits. Export daily positions and returns.

Local results are not WorldQuant BRAIN results. Data quality, survivorship, corporate actions, costs and execution assumptions can materially change outcomes.

## GitHub
Create a repository (suggested name: `alpha-king`), push these files to its default branch, then deploy that branch on Streamlit Community Cloud. This ZIP does not create or push a remote repository.
