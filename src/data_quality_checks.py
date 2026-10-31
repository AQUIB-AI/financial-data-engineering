
from pathlib import Path
import pandas as pd

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load datasets
entries = pd.read_csv(DATA_DIR / "journal_entries.csv")
lines = pd.read_csv(DATA_DIR / "journal_entry_lines.csv")
accounts = pd.read_csv(DATA_DIR / "chart_of_accounts.csv")
companies = pd.read_csv(DATA_DIR / "companies.csv")
trial_balances = pd.read_csv(DATA_DIR / "trial_balances.csv")


# ============================================================
# 2. HELPER FUNCTION
# ============================================================

def save_report(name, dataframe):
    """Save a data-quality report to the outputs directory."""
    path = OUTPUT_DIR / name
    dataframe.to_csv(path, index=False)
    print(f"Saved: {path.name} ({len(dataframe):,} rows)")


# ============================================================
# 3. DATASET PROFILE
# ============================================================

datasets = {
    "journal_entries": entries,
    "journal_entry_lines": lines,
    "chart_of_accounts": accounts,
    "companies": companies,
    "trial_balances": trial_balances,
}

profile = []

for name, df in datasets.items():
    profile.append({
        "dataset": name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
    })

profile_df = pd.DataFrame(profile)
save_report("dataset_profile.csv", profile_df)


# ============================================================
# 4. MISSING VALUES BY COLUMN
# ============================================================

missing_records = []

for name, df in datasets.items():
    missing = df.isna().sum()

    for column, count in missing.items():
        if count > 0:
            missing_records.append({
                "dataset": name,
                "column": column,
                "missing_count": int(count),
                "missing_percentage": round(
                    count / len(df) * 100, 2
                ) if len(df) else 0,
            })

missing_df = pd.DataFrame(
    missing_records,
    columns=[
        "dataset",
        "column",
        "missing_count",
        "missing_percentage",
    ],
)
save_report("missing_values_report.csv", missing_df)


# ============================================================
# 5. DUPLICATE ROWS
# ============================================================

duplicate_records = []

for name, df in datasets.items():
    duplicates = df[df.duplicated(keep=False)].copy()

    if not duplicates.empty:
        duplicates.insert(0, "dataset", name)
        duplicate_records.append(duplicates)

if duplicate_records:
    duplicate_df = pd.concat(
        duplicate_records,
        ignore_index=True,
    )
else:
    duplicate_df = pd.DataFrame(
        columns=["dataset"] + list(entries.columns)
    )

save_report("duplicate_rows_report.csv", duplicate_df)


# ============================================================
# 6. INVALID DEBIT AND CREDIT AMOUNTS
# ============================================================

debit = pd.to_numeric(lines["debit"], errors="coerce")
credit = pd.to_numeric(lines["credit"], errors="coerce")

negative_amounts = lines[
    (debit < 0) | (credit < 0)
].copy()

save_report("negative_amounts_report.csv", negative_amounts)

# Both debit and credit are positive on the same line.
both_sides_positive = lines[
    (debit > 0) & (credit > 0)
].copy()

save_report(
    "both_debit_credit_positive_report.csv",
    both_sides_positive,
)

# Missing or non-numeric debit/credit amounts.
invalid_amounts = lines[
    debit.isna() | credit.isna()
].copy()

save_report("invalid_amounts_report.csv", invalid_amounts)


# ============================================================
# 7. REFERENTIAL INTEGRITY
# ============================================================

# Journal lines must reference an existing journal entry.
missing_entries = lines[
    ~lines["journal_entry_id"].isin(entries["id"])
].copy()

save_report(
    "orphan_journal_entry_lines.csv",
    missing_entries,
)

# Journal lines must reference an existing account.
missing_accounts = lines[
    ~lines["account_id"].isin(accounts["id"])
].copy()

save_report(
    "orphan_account_lines.csv",
    missing_accounts,
)


# ============================================================
# 8. JOURNAL ENTRY DEBIT-CREDIT RECONCILIATION
# ============================================================

reconciliation_lines = lines.copy()

reconciliation_lines["debit"] = pd.to_numeric(
    reconciliation_lines["debit"],
    errors="coerce",
)

reconciliation_lines["credit"] = pd.to_numeric(
    reconciliation_lines["credit"],
    errors="coerce",
)

reconciliation = (
    reconciliation_lines
    .groupby("journal_entry_id", dropna=False)
    .agg(
        total_debit=("debit", "sum"),
        total_credit=("credit", "sum"),
        line_count=("id", "count"),
    )
    .reset_index()
)

reconciliation["difference"] = (
    reconciliation["total_debit"]
    - reconciliation["total_credit"]
).round(2)

reconciliation["is_balanced"] = (
    reconciliation["difference"].abs() <= 0.01
)

unbalanced_entries = reconciliation[
    ~reconciliation["is_balanced"]
].copy()

save_report(
    "unbalanced_journal_entries.csv",
    unbalanced_entries,
)

save_report(
    "journal_entry_reconciliation.csv",
    reconciliation,
)


# ============================================================
# 9. ACCOUNT AND COMPANY VALIDATION
# ============================================================

# Check that account company IDs exist in the companies table.
accounts_with_missing_company = accounts[
    ~accounts["company_id"].isin(companies["id"])
].copy()

save_report(
    "accounts_with_missing_company.csv",
    accounts_with_missing_company,
)

# Check that journal entry company IDs exist.
entries_with_missing_company = entries[
    ~entries["company_id"].isin(companies["id"])
].copy()

save_report(
    "entries_with_missing_company.csv",
    entries_with_missing_company,
)


# ============================================================
# 10. SUMMARY
# ============================================================

summary = pd.DataFrame([
    {
        "check": "Journal entry lines",
        "issue_count": len(lines),
    },
    {
        "check": "Duplicate journal entry lines",
        "issue_count": int(lines.duplicated().sum()),
    },
    {
        "check": "Negative debit/credit amounts",
        "issue_count": len(negative_amounts),
    },
    {
        "check": "Both debit and credit positive",
        "issue_count": len(both_sides_positive),
    },
    {
        "check": "Invalid or missing debit/credit",
        "issue_count": len(invalid_amounts),
    },
    {
        "check": "Lines with missing journal entries",
        "issue_count": len(missing_entries),
    },
    {
        "check": "Lines with missing accounts",
        "issue_count": len(missing_accounts),
    },
    {
        "check": "Unbalanced journal entries",
        "issue_count": len(unbalanced_entries),
    },
    {
        "check": "Accounts with missing companies",
        "issue_count": len(accounts_with_missing_company),
    },
    {
        "check": "Entries with missing companies",
        "issue_count": len(entries_with_missing_company),
    },
])

save_report("data_quality_summary.csv", summary)

print("\n" + "=" * 60)
print("DATA QUALITY VALIDATION COMPLETED")
print("=" * 60)
print(summary.to_string(index=False))
print(f"\nAll reports saved in: {OUTPUT_DIR}")
