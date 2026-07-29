from backend.parser import _parse_score, parse_credit_report
from pathlib import Path


def expect(text: str, expected: int, source_contains: str = "") -> None:
    result = _parse_score(text)
    assert result["value"] == expected, result
    assert result["found"] is True, result
    if source_contains:
        assert source_contains.lower() in result["source"].lower(), result


def main() -> None:
    expect(
        """Consumer Score Information\nScore Date Exception Code Risk Category Final Score\n2026-07-16 Potential High Risk 553\n440 530 610 700 780 870 960\nDebt Summary""",
        553,
        "table",
    )
    expect(
        """Credit Score Information\n440 530 610 700 780 870 960\nFinal Score: 621\nRisk Category: Medium Risk\nDebt Summary""",
        621,
        "label",
    )
    expect(
        """Consumer Score Information\nScore Date Exception Code Risk Category Final Score\n2026-07-16\n001\nPotential High Risk\n577\n440 530 610 700 780 870 960\nDebt Summary""",
        577,
        "split",
    )
    expect(
        """Consumer Credit Score\nReport number 2788037\nYour credit score is 0\nDebt Summary""",
        0,
        "score",
    )
    expect(
        """Consumer Score Information\nCredit Score = 648\nTotal Outstanding Debt 125000\nDebt Summary""",
        648,
        "label",
    )
    missing = _parse_score("Debt Summary\nTotal Monthly Instalments 850\nTotal Outstanding Debt 90000")
    assert missing["value"] is None and missing["needsReview"] is True, missing

    sample_expectations = {
        "REF2788037.pdf": 553,
        "REF2788225.pdf": 566,
    }
    for filename, expected in sample_expectations.items():
        report = Path("/mnt/data") / filename
        parsed = parse_credit_report(report.read_bytes(), filename, supplied_password="DN13084")
        client = parsed["client"]
        assert client["creditScore"] == expected, client
        assert client["scoreConfidence"] >= 95, client
        assert client["scoreNeedsReview"] is False, client
        assert "Final Score" in client["scoreSource"], client
        print(
            f"{filename}: score={client['creditScore']} "
            f"source={client['scoreSource']} confidence={client['scoreConfidence']}%"
        )

    print("Score parser repair tests passed.")


if __name__ == "__main__":
    main()
