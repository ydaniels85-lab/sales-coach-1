from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "smoke.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        sample_password = os.environ.get("FINTASTIC_SAMPLE_PASSWORD", "")
        if sample_password:
            os.environ["DEFAULT_CREDIT_REPORT_PDF_PASSWORD"] = sample_password

        from backend.app import app, initialize_database
        from backend.parser import build_sales_coach

        score_zero_removal = build_sales_coach(
            {}, 0, True, False, [],
        )
        assert score_zero_removal["service"] == "Debt Review Removal"
        assert score_zero_removal["flags"]["scoreZeroRule"] is True
        assert score_zero_removal["additionalServices"] == []

        score_zero_with_balances = build_sales_coach(
            {}, 0, True, False,
            [{
                "included": True,
                "currentBalance": 12000,
                "arrears": 500,
                "monthlyInstallment": 900,
                "reducedAmount": 600,
                "isAsset": False,
                "isFurniture": False,
            }],
        )
        assert score_zero_with_balances["service"] == "Debt Review Removal"
        assert score_zero_with_balances["additionalServices"] == ["Debt Mediation"]
        assert score_zero_with_balances["flags"]["doubleSaleCandidate"] is True

        cpi_100 = build_sales_coach({}, 100, True, False, [])
        assert cpi_100["service"] == "Credit Profile Investigation"
        assert cpi_100["flags"]["scoreInCpiRange"] is True
        assert cpi_100["flags"]["hasOutstandingBalances"] is False

        cpi_600 = build_sales_coach({}, 600, True, False, [])
        assert cpi_600["service"] == "Credit Profile Investigation"
        assert cpi_600["pricing"]["onceOff"] == 3000
        assert [plan["monthlyAmount"] for plan in cpi_600["pricing"]["paymentPlans"]] == [3000, 1500, 1000, 750]
        assert len(cpi_600["goldenQuestions"]) == 5
        assert len(cpi_600["objectionHandlers"]) >= 5

        score_601_no_balances = build_sales_coach({}, 601, True, False, [])
        assert score_601_no_balances["service"] == "Needs Manual Review"
        assert score_601_no_balances["flags"]["creditProfileInvestigationCandidate"] is False

        low_instalment_no_longer_cpi = build_sales_coach(
            {}, 700, True, False,
            [{
                "included": True,
                "currentBalance": 0,
                "arrears": 0,
                "monthlyInstallment": 900,
                "reducedAmount": 600,
                "isAsset": False,
                "isFurniture": False,
            }],
        )
        assert low_instalment_no_longer_cpi["service"] == "Needs Manual Review"

        score_500_with_balances = build_sales_coach(
            {}, 500, True, False,
            [{
                "included": True,
                "currentBalance": 12000,
                "arrears": 0,
                "monthlyInstallment": 1200,
                "reducedAmount": 800,
                "isAsset": False,
                "isFurniture": False,
            }],
        )
        assert score_500_with_balances["service"] == "Debt Mediation"
        assert score_500_with_balances["flags"]["creditProfileInvestigationCandidate"] is False

        removal_flag_with_balances = build_sales_coach(
            {}, 400, True, True,
            [{
                "included": True,
                "currentBalance": 12000,
                "arrears": 500,
                "monthlyInstallment": 500,
                "reducedAmount": 350,
                "isAsset": False,
                "isFurniture": False,
            }],
        )
        assert removal_flag_with_balances["service"] == "Debt Review Removal"
        assert removal_flag_with_balances["additionalServices"] == ["Debt Mediation"]

        initialize_database()
        client = app.test_client()

        health = client.get("/api/health")
        assert health.status_code == 200, health.get_json()
        assert health.get_json()["authenticationRequired"] is False

        created = client.post("/api/clients", json={"applicationType": "Joint"})
        assert created.status_code == 201, created.get_json()
        client_id = created.get_json()["client"]["id"]

        updated = client.patch(
            f"/api/clients/{client_id}",
            json={
                "applicationType": "Joint",
                "firstName": "Test",
                "surname": "Client",
                "idNumber": "8001015009087",
                "phone": "0711111111",
                "email": "test@example.com",
                "physicalAddress": "1 Main Road, Cape Town",
                "employer": "Example Ltd",
                "nettSalary": 15000,
                "creditScore": 500,
                "scoreFound": True,
                "scoreNeedsReview": False,
                "scoreManuallyVerified": True,
                "bank": {
                    "accountHolder": "Test Client",
                    "bankName": "FNB",
                    "accountType": "Cheque / Current",
                    "branchCode": "250655",
                    "accountNumber": "1234567890",
                },
                "spouse": {
                    "firstName": "Joint",
                    "surname": "Client",
                    "idNumber": "8202020009088",
                    "phone": "0722222222",
                    "email": "joint@example.com",
                    "employer": "Joint Ltd",
                    "nettSalary": 12000,
                    "bank": {
                        "accountHolder": "Joint Client",
                        "bankName": "Capitec",
                        "accountType": "Savings",
                        "branchCode": "470010",
                        "accountNumber": "9876543210",
                    },
                },
            },
        )
        assert updated.status_code == 200, updated.get_json()
        body = updated.get_json()["client"]
        assert body["applicationType"] == "Joint"
        assert body["bank"]["bankName"] == "FNB"
        assert body["spouse"]["bank"]["bankName"] == "Capitec"
        assert body["fullName"] == "Test Client"
        assert body["spouse"]["fullName"] == "Joint Client"
        assert body["creditScore"] == 500
        assert body["scoreManuallyVerified"] is True
        assert body["scoreNeedsReview"] is False
        assert body["serviceType"] == "Credit Profile Investigation"

        report_path = Path(os.environ.get("FINTASTIC_SAMPLE_REPORT", ""))
        if sample_password and report_path.exists():
            report_bytes = report_path.read_bytes()
            first = client.post(
                "/api/upload/credit-report",
                data={"file": (io.BytesIO(report_bytes), report_path.name)},
                content_type="multipart/form-data",
            )
            assert first.status_code == 423, first.get_json()
            assert first.get_json()["code"] == "PDF_PASSWORD_REQUIRED"

            correct = client.post(
                "/api/upload/credit-report",
                data={"file": (io.BytesIO(report_bytes), report_path.name), "pdfPassword": sample_password},
                content_type="multipart/form-data",
            )
            assert correct.status_code in {200, 201}, correct.get_json()
            assert correct.get_json()["client"]["report"]["bureau"] == "Datanamix"
            assert len(correct.get_json()["client"]["accounts"]) > 0

        print("API smoke test passed: score-zero removal, removal-plus-mediation, CPI 100-600/no-balances/no-flag, client capture and protected-PDF flow.")


if __name__ == "__main__":
    main()
