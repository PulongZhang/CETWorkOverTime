from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.dependencies import get_repository
from app.main import app


class FakeRepository:
    target_hours = 36.0

    def get_all_years(self) -> list[int]:
        return [2026]

    def get_diligence_stats(self, year: int) -> dict:
        return {
            "year": year,
            "months": [
                {
                    "month": 7,
                    "hours": 40.0,
                    "entries": 2,
                    "target": 36.0,
                    "delta": 4.0,
                }
            ],
            "total_hours": 40.0,
            "total_target": 36.0,
            "total_delta": 4.0,
        }

    def get_emails_by_month(self, year: int, month: int) -> list[dict]:
        return [
            {
                "email_date": f"{year}-{month:02d}-30",
                "subject": "工作日志",
                "content": "完成迁移",
                "diligence_start": "18:00",
                "diligence_end": "20:00",
                "diligence_hours": 2.0,
            }
        ]

    def get_email_by_date(self, email_date: object) -> dict | None:
        return None


class UnavailableRepository(FakeRepository):
    def get_all_years(self) -> list[int]:
        raise OperationalError(None, None, ConnectionError("database unavailable"))

    def get_emails_by_month(self, year: int, month: int) -> list[dict]:
        raise OperationalError(None, None, ConnectionError("database unavailable"))


def login(client: TestClient) -> None:
    with patch("app.api.v1.auth.pyotp.TOTP.verify", return_value=True):
        response = client.post("/api/v1/auth/login", json={"code": "123456"})
    assert response.status_code == 200


def test_business_api_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/diligence")

    assert response.status_code == 401


def test_login_sets_session_and_logout_clears_it() -> None:
    client = TestClient(app)

    login(client)
    assert client.get("/api/v1/auth/session").json() == {"authenticated": True}

    response = client.post("/api/v1/auth/logout")
    assert response.json() == {"authenticated": False}
    assert client.get("/api/v1/auth/session").json() == {"authenticated": False}


def test_diligence_and_report_api_use_repository() -> None:
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    client = TestClient(app)
    login(client)

    diligence = client.get("/api/v1/diligence")
    report = client.get("/api/v1/reports/2026/7")

    assert diligence.status_code == 200
    assert diligence.json()["years"]["2026"]["total_hours"] == 40.0
    assert report.status_code == 200
    assert "完成迁移" in report.json()["markdown"]
    assert "<h1>2026年07月工作总结</h1>" in report.json()["html"]

    app.dependency_overrides.clear()


def test_database_errors_return_service_unavailable() -> None:
    app.dependency_overrides[get_repository] = lambda: UnavailableRepository()
    client = TestClient(app)
    login(client)

    try:
        responses = [
            client.get("/api/v1/diligence"),
            client.get("/api/v1/reports"),
            client.get("/api/v1/emails?year=2026&month=7"),
        ]

        for response in responses:
            assert response.status_code == 503
            assert response.json() == {"detail": "数据库暂时不可用，请稍后重试"}
    finally:
        app.dependency_overrides.clear()
