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

        cpi = build_sales_coach(
            {}, 620, True, False,
            [{
                "included": True,
                "currentBalance": 12000,
                "arrears": 0,
                "monthlyInstallment": 900,
                "reducedAmount": 600,
                "isAsset": False,
                "isFurniture": False,
            }],
        )
        assert cpi["service"] == "Credit Profile Investigation"
        assert cpi["headline"] == "Potential Credit Profile Investigation sale"
        assert cpi["pricing"]["onceOff"] == 3000
        assert [plan["monthlyAmount"] for plan in cpi["pricing"]["paymentPlans"]] == [3000, 1500, 1000, 750]

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

        print("API smoke test passed: open access, client capture, joint banking, CPI pricing and protected-PDF flow.")


if __name__ == "__main__":
    main()
