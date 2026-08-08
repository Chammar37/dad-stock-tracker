"""One-time CSV to Supabase migration.

Run with Supabase storage configured in Streamlit secrets or with
STOCK_TRACKER_STORAGE_BACKEND=supabase. This script prints row counts only and
never prints credential values.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.data_manager import DataManager
from utils.supabase_data_manager import SupabaseDataManager


def main() -> int:
    data_dir = os.environ.get("STOCK_TRACKER_DATA_DIR", "data")
    csv_manager = DataManager(data_dir=data_dir)
    sql_manager = SupabaseDataManager()

    consolidated = csv_manager.read_consolidated()
    trades = csv_manager.read_trades()

    if not sql_manager.write_consolidated(consolidated):
        print("Failed to migrate holdings")
        return 1
    if not sql_manager.write_trades(trades):
        print("Failed to migrate trades")
        return 1

    migrated_holdings = len(sql_manager.read_consolidated())
    migrated_trades = len(sql_manager.read_trades())
    print(
        "Migration complete: "
        f"{migrated_holdings}/{len(consolidated)} holdings, "
        f"{migrated_trades}/{len(trades)} trades"
    )
    if migrated_holdings != len(consolidated) or migrated_trades != len(trades):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
