# Escape Velocity Desktop

A minimalist desktop financial independence dashboard built from the spreadsheet concept.

## What it does

- Estimates federal, payroll, state, and selected local wage taxes from filing status, state, and city.
- Calculates after-tax cash income, monthly investment capacity, savings rate, FI number, and FI progress.
- Projects portfolio growth, expense growth, debt payoff, and the age at which investments may cover lifestyle expenses.
- Compares scenarios such as investing more, cutting low-value spending, lower returns, and higher income growth.
- Includes concise savings/investing education inside the app.
- Saves a local profile and exports projection data to CSV.

## Run it

### Windows

1. Install Python 3.11+ from python.org.
2. Open this folder.
3. Double-click `run_windows.bat`, or run:

```bash
py main.py
```

### macOS / Linux

```bash
python3 main.py
```

No third-party Python packages are required. The app uses Tkinter from the Python standard library.

## Files

- `main.py` — desktop app UI
- `engine.py` — financial projection and tax logic
- `tax_data.py` — federal/state/local tax data module
- `education.py` — concise education cards
- `test_engine.py` — calculation tests

## Tax model notes

The app uses tax year 2026 federal brackets, 2026 standard deductions, 2026 payroll tax parameters, flat/no-tax state rules, progressive state rate ranges, and a compact starter table of common city/local wage taxes.

The state/local estimator is suitable for planning, not filing. Exact local tax coverage requires a larger jurisdiction-level dataset.

## Test it

```bash
python3 -m unittest test_engine.py
```

Windows:

```bash
py -m unittest test_engine.py
```
