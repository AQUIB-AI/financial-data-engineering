# Financial Data Engineering & Audit Analytics

A Python- and SQL-based financial analytics project designed to analyze journal entries, validate financial data quality, and generate monthly financial summaries for audit reporting.

## Project Overview

This project demonstrates how Python, SQL, and SQLite can be used to build a financial data analytics pipeline. It processes financial datasets, performs data quality checks, and generates reports that can be visualized using Tableau Public.

## Technologies Used

- Python
- Pandas
- SQL
- SQLite
- Tableau Public
- Git and GitHub

## Key Features

- Financial dataset inspection and analysis
- SQL-based analytics using SQLite
- Duplicate record detection
- Validation of debit and credit amounts
- Journal entry balance checks
- Detection of missing references and orphan records
- Monthly financial summaries
- CSV report generation for dashboarding

## Project Structure

```text
financial-data-engineering/
├── data/
│   └── raw/
├── outputs/
├── src/
│   ├── financial_analysis.py
│   ├── sql_analytics.py
│   ├── data_quality_checks.py
│   └── financial_summary.py
├── .gitignore
└── README.md
```

## How to Run

1. Clone this repository.
2. Create and activate a Python virtual environment.
3. Install the required dependencies.
4. Run the scripts from the project root.

Example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas
python src/financial_analysis.py
python src/sql_analytics.py
python src/data_quality_checks.py
python src/financial_summary.py
```

## Dashboard

The Tableau dashboard visualizes monthly journal entry activity, debit and credit trends, and data quality indicators.

Dashboard screenshots will be added here.

## Outputs

The `outputs/` directory contains generated CSV reports, including monthly summaries and data quality results.

## Disclaimer

This project is intended for educational and portfolio purposes. The results depend on the dataset used and should not be treated as professional financial or audit advice.
