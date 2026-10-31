from pathlib import Path
import sqlite3
import pandas as pd

# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "outputs"
DB_PATH = PROJECT_DIR / "financial_analytics.db"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. CONNECT TO DATABASE
# ==========================================

def connect_database():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run sql_analytics.py first."
        )

    return sqlite3.connect(DB_PATH)


# ==========================================
# 3. INSPECT DATABASE TABLES
# ==========================================

def get_tables(connection):
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """

    return pd.read_sql_query(query, connection)["name"].tolist()


# ==========================================
# 4. GENERATE TABLE ROW COUNTS
# ==========================================

def generate_table_summary(connection, tables):
    results = []

    for table in tables:
        # Table names originate from sqlite_master.
        safe_table = '"' + table.replace('"', '""') + '"'

        query = f"SELECT COUNT(*) AS row_count FROM {safe_table}"
        row_count = pd.read_sql_query(query, connection).iloc[0]["row_count"]

        results.append({
            "table_name": table,
            "row_count": int(row_count)
        })

    summary = pd.DataFrame(results)
    summary.to_csv(OUTPUT_DIR / "table_summary.csv", index=False)

    print("\nDATABASE TABLE SUMMARY")
    print("=" * 60)

    if summary.empty:
        print("No tables found.")
    else:
        print(summary.to_string(index=False))

    return summary


# ==========================================
# 5. ANALYSE JOURNAL ENTRY BALANCES
# ==========================================

def analyse_journal_balances(connection, tables):
    required_tables = {"journal_entry_lines", "journal_entries"}

    if not required_tables.issubset(set(tables)):
        print(
            "\nJournal balance analysis skipped: "
            "required tables were not found."
        )
        return None

    query = """
        SELECT
            je.id AS journal_entry_id,
            je.entry_date,
            COALESCE(SUM(jel.debit), 0) AS total_debits,
            COALESCE(SUM(jel.credit), 0) AS total_credits,
            ROUND(
                COALESCE(SUM(jel.debit), 0)
                - COALESCE(SUM(jel.credit), 0),
                2
            ) AS difference
        FROM journal_entries AS je
        LEFT JOIN journal_entry_lines AS jel
            ON je.id = jel.journal_entry_id
        GROUP BY je.id, je.entry_date
        ORDER BY je.entry_date, je.id;
    """

    balances = pd.read_sql_query(query, connection)

    balances["is_balanced"] = (
        balances["difference"].abs() < 0.01
    )

    balances.to_csv(
        OUTPUT_DIR / "journal_balance_summary.csv",
        index=False
    )

    print("\nJOURNAL BALANCE SUMMARY")
    print("=" * 60)
    print(f"Journal entries analysed: {len(balances):,}")
    print(f"Balanced entries: {balances['is_balanced'].sum():,}")
    print(f"Unbalanced entries: {(~balances['is_balanced']).sum():,}")

    return balances


# ==========================================
# 6. CREATE MONTHLY ACTIVITY SUMMARY
# ==========================================

def generate_monthly_summary(balances):
    if balances is None or balances.empty:
        print("\nMonthly summary skipped: no journal data available.")
        return None

    balances = balances.copy()

    balances["entry_date"] = pd.to_datetime(
        balances["entry_date"],
        errors="coerce"
    )

    balances = balances.dropna(subset=["entry_date"])

    if balances.empty:
        print("\nMonthly summary skipped: no valid entry dates.")
        return None

    balances["entry_month"] = (
        balances["entry_date"].dt.to_period("M").astype(str)
    )

    monthly = (
        balances.groupby("entry_month", as_index=False)
        .agg(
            journal_entry_count=("journal_entry_id", "count"),
            total_debits=("total_debits", "sum"),
            total_credits=("total_credits", "sum"),
            unbalanced_entries=(
                "is_balanced",
                lambda values: int((~values).sum())
            )
        )
    )

    monthly["total_debits"] = monthly["total_debits"].round(2)
    monthly["total_credits"] = monthly["total_credits"].round(2)

    monthly.to_csv(
        OUTPUT_DIR / "monthly_financial_summary.csv",
        index=False
    )

    print("\nMONTHLY FINANCIAL ACTIVITY")
    print("=" * 60)
    print(monthly.to_string(index=False))

    return monthly


# ==========================================
# 7. MAIN PROGRAM
# ==========================================

def main():
    print("=" * 60)
    print("FINANCIAL DATA ENGINEERING SUMMARY")
    print("=" * 60)

    connection = connect_database()

    try:
        tables = get_tables(connection)

        if not tables:
            print("No tables found in the database.")
            return

        generate_table_summary(connection, tables)

        balances = analyse_journal_balances(connection, tables)

        generate_monthly_summary(balances)

        print("\nSUMMARY GENERATION COMPLETED")
        print(f"Database: {DB_PATH}")
        print(f"Reports saved in: {OUTPUT_DIR}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()