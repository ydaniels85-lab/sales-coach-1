from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parser import parse_credit_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    expected = {"REF2788037.pdf": 5, "REF2788225.pdf": 9}
    for report in args.reports:
        result = parse_credit_report(report.read_bytes(), report.name, supplied_password=args.password)
        accounts = result["accounts"]
        client = result["client"]
        print(f"{report.name}: {client['fullName']} | ID {client['idNumber']} | score {client['creditScore']} | accounts {len(accounts)}")
        if report.name in expected:
            assert len(accounts) == expected[report.name], f"Expected {expected[report.name]} accounts, got {len(accounts)}"
        assert result["pdf"]["encrypted"] is True
        assert client["report"]["bureau"] == "Datanamix"
    print("All supplied sample reports parsed successfully.")


if __name__ == "__main__":
    main()
