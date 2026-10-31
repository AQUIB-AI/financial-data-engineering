
from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = PROJECT_DIR / "financial_analytics.db"


# ============================================================
# 2. LOAD CSV FILES INTO SQLITE
# ============================================================

def load_tables(connection):
    """Load accounting CSV files into SQLite tables."""

    files = {
        "companies": "companies.csv",
        "chart_of_accounts": "chart_of_accounts.csv",
        "journal_entries": "journal_entries.csv",
        "journal_entry_lines": "journal_entry_lines.csv",
        "trial_balances": "trial_balances.csv",
    }

    for table_name, filename in files.items():
        file_path = DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        df = pd.read_csv(file_path)

        # Replace tables on each run to avoid stale data.
        df.to_sql(
            table_name,
            connection,
            if_exists="replace",
            index=False,
        )

        print(f"Loaded {len(df):,} rows into {table_name}")


# ============================================================
# 3. SQL ANALYTICS
# ============================================================

QUERIES = {
    "account_summary": """
        SELECT
            coa.code AS account_code,
            coa.name AS account_name,
            coa.account_type,
            COUNT(DISTINCT jel.journal_entry_id) AS journal_entries,
            ROUND(SUM(COALESCE(jel.debit, 0)), 2) AS total_debits,
            ROUND(SUM(COALESCE(jel.credit, 0)), 2) AS total_credits,
            ROUND(
                SUM(COALESCE(jel.debit, 0))
                - SUM(COALESCE(jel.credit, 0)),
                2
            ) AS net_debit
        FROM chart_of_accounts AS coa
        LEFT JOIN journal_entry_lines AS jel
            ON coa.id = jel.account_id
        GROUP BY coa.id, coa.code, coa.name, coa.account_type
        ORDER BY total_debits + total_credits DESC
    """,

    "monthly_activity": """
        SELECT
            substr(je.entry_date, 1, 7) AS entry_month,
            COUNT(DISTINCT je.id) AS journal_entry_count,
            ROUND(SUM(COALESCE(jel.debit, 0)), 2) AS total_debits,
            ROUND(SUM(COALESCE(jel.credit, 0)), 2) AS total_credits
        FROM journal_entries AS je
        JOIN journal_entry_lines AS jel
            ON je.id = jel.journal_entry_id
        GROUP BY substr(je.entry_date, 1, 7)
        ORDER BY entry_month
    """,

    "high_value_lines": """
        SELECT
            je.entry_number,
            je.entry_date,
            je.description AS entry_description,
            coa.code AS account_code,
            coa.name AS account_name,
            jel.description AS line_description,
            jel.debit,
            jel.credit,
            MAX(
                COALESCE(jel.debit, 0),
                COALESCE(jel.credit, 0)
            ) AS line_amount
        FROM journal_entry_lines AS jel
        JOIN journal_entries AS je
            ON je.id = jel.journal_entry_id
        LEFT JOIN chart_of_accounts AS coa
            ON coa.id = jel.account_id
        ORDER BY line_amount DESC
        LIMIT 100
    """,

    "posting_status": """
        SELECT
            posted,
            is_adjusting,
            is_reversal,
            COUNT(*) AS entry_count
        FROM journal_entries
        GROUP BY posted, is_adjusting, is_reversal
        ORDER BY entry_count DESC
    """,

    "referential_integrity": """
        SELECT
            COUNT(*) AS total_lines,
            SUM(
                CASE WHEN je.id IS NULL THEN 1 ELSE 0 END
            ) AS missing_journal_entry
        FROM journal_entry_lines AS jel
        LEFT JOIN journal_entries AS je
            ON je.id = jel.journal_entry_id
    """,
}


def run_queries(connection):
    """Execute SQL queries and export their results."""

    for report_name, query in QUERIES.items():
        print(f"\n{'=' * 60}")
        print(f"SQL REPORT: {report_name}")
        print("=" * 60)

        result = pd.read_sql_query(query, connection)

        print(result.head(10).to_string(index=False))

        output_path = OUTPUT_DIR / f"{report_name}.csv"
        result.to_csv(output_path, index=False)

        print(f"\nSaved report: {output_path.name}")


# ============================================================
# 4. MAIN PIPELINE
# ============================================================

def main():
    print("=" * 60)
    print("FINANCIAL SQL ANALYTICS PIPELINE")
    print("=" * 60)

    with sqlite3.connect(DB_PATH) as connection:
        load_tables(connection)
        run_queries(connection)

    print("\nSQL ANALYTICS COMPLETED")
    print(f"Database: {DB_PATH}")
    print(f"Reports: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
