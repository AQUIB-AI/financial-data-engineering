
from pathlib import Path

import pandas as pd


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    "chart_of_accounts.csv",
    "companies.csv",
    "journal_entries.csv",
    "journal_entry_lines.csv",
    "trial_balances.csv",
]


# ============================================================
# 2. DATA QUALITY ASSESSMENT
# ============================================================

def inspect_dataset(filename):
    """Inspect a CSV file and generate a data-quality report."""

    file_path = DATA_DIR / filename

    print("\n" + "=" * 65)
    print(f"DATA QUALITY ASSESSMENT: {filename}")
    print("=" * 65)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return None

    df = pd.read_csv(file_path)

    print(f"Total rows: {len(df):,}")
    print(f"Total columns: {len(df.columns)}")

    print("\nColumn names:")
    print(list(df.columns))

    # Identify missing values.
    missing = df.isnull().sum()

    print("\nMissing values:")
    if missing.sum() == 0:
        print("No missing values detected.")
    else:
        print(missing[missing > 0].to_string())

    # Identify completely duplicated rows.
    duplicate_count = int(df.duplicated().sum())
    print(f"\nDuplicate rows: {duplicate_count:,}")

    # Generate a column-level quality report.
    summary = pd.DataFrame({
        "column": df.columns,
        "data_type": [str(dtype) for dtype in df.dtypes],
        "missing_values": df.isnull().sum().values,
        "missing_percentage": (
            df.isnull().mean().values * 100
        ).round(2),
    })

    summary["duplicate_rows_in_dataset"] = duplicate_count

    report_name = f"{Path(filename).stem}_quality_report.csv"
    report_path = OUTPUT_DIR / report_name

    summary.to_csv(report_path, index=False)

    print(f"\nQuality report saved: {report_path.name}")

    return df


def run_data_quality_assessment():
    """Assess all configured accounting datasets."""

    print("\n" + "#" * 65)
    print("FINANCIAL DATA ENGINEERING PIPELINE")
    print("STAGE 1: DATA QUALITY ASSESSMENT")
    print("#" * 65)

    datasets = {}

    for filename in FILES:
        df = inspect_dataset(filename)

        if df is not None:
            datasets[filename] = df

    print("\nData-quality assessment completed.")
    print(f"Reports directory: {OUTPUT_DIR}")

    return datasets


# ============================================================
# 3. FINANCIAL RECONCILIATION
# ============================================================

def reconcile_journal_entries():
    """
    Aggregate debit and credit amounts for each journal entry.

    Entries whose debit and credit totals differ by more than
    one cent are flagged for review.
    """

    print("\n" + "#" * 65)
    print("STAGE 2: FINANCIAL RECONCILIATION")
    print("#" * 65)

    lines_path = DATA_DIR / "journal_entry_lines.csv"

    if not lines_path.exists():
        print(f"ERROR: File not found: {lines_path}")
        return None

    lines = pd.read_csv(lines_path)

    required_columns = {
        "id",
        "journal_entry_id",
        "debit",
        "credit",
    }

    missing_columns = required_columns - set(lines.columns)

    if missing_columns:
        print(f"ERROR: Required columns are missing: {missing_columns}")
        return None

    # Preserve the original data and identify invalid amounts.
    for column in ["debit", "credit"]:
        original_values = lines[column]
        numeric_values = pd.to_numeric(
            original_values,
            errors="coerce",
        )

        invalid_mask = (
            original_values.notna()
            & numeric_values.isna()
        )

        print(
            f"Invalid nonnumeric {column} values: "
            f"{int(invalid_mask.sum()):,}"
        )

        lines[column] = numeric_values

    # Count rows that contain missing debit or credit values.
    missing_amount_mask = lines[["debit", "credit"]].isna().any(axis=1)

    print(
        "Rows with missing debit or credit: "
        f"{int(missing_amount_mask.sum()):,}"
    )

    # For reconciliation only, interpret a missing amount as zero.
    # The original missing values are reported above.
    lines[["debit", "credit"]] = lines[
        ["debit", "credit"]
    ].fillna(0)

    # Aggregate the transaction lines by journal entry.
    reconciliation = (
        lines.groupby("journal_entry_id", as_index=False)
        .agg(
            total_debit=("debit", "sum"),
            total_credit=("credit", "sum"),
            line_count=("id", "count"),
        )
    )

    # Calculate the difference between debits and credits.
    reconciliation["difference"] = (
        reconciliation["total_debit"]
        - reconciliation["total_credit"]
    ).round(2)

    # Flag entries that require review.
    reconciliation["reconciliation_status"] = (
        reconciliation["difference"]
        .abs()
        .le(0.01)
        .map({
            True: "BALANCED",
            False: "REVIEW_REQUIRED",
        })
    )

    # Save all reconciliation results.
    report_path = OUTPUT_DIR / "journal_reconciliation_report.csv"

    reconciliation.to_csv(report_path, index=False)

    # Summarise the results.
    total_entries = len(reconciliation)

    balanced_count = int(
        (reconciliation["reconciliation_status"] == "BALANCED").sum()
    )

    review_count = int(
        (
            reconciliation["reconciliation_status"]
            == "REVIEW_REQUIRED"
        ).sum()
    )

    print(f"\nJournal entries analysed: {total_entries:,}")
    print(f"Balanced entries: {balanced_count:,}")
    print(f"Entries requiring review: {review_count:,}")

    if total_entries:
        balanced_percentage = balanced_count / total_entries * 100
        print(f"Balanced entries percentage: {balanced_percentage:.2f}%")

    print(f"\nReconciliation report saved: {report_path}")

    # Display the first ten exceptions, if any.
    exceptions = reconciliation[
        reconciliation["reconciliation_status"] == "REVIEW_REQUIRED"
    ]

    print("\nSample entries requiring review:")

    if exceptions.empty:
        print("No unbalanced entries detected.")
    else:
        print(exceptions.head(10).to_string(index=False))

    return reconciliation


# ============================================================
# 4. PIPELINE ENTRY POINT
# ============================================================

def main():
    """Execute the data-quality and reconciliation stages."""

    run_data_quality_assessment()
    reconcile_journal_entries()

    print("\n" + "=" * 65)
    print("FINANCIAL DATA PIPELINE COMPLETED")
    print(f"All reports are saved in: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
