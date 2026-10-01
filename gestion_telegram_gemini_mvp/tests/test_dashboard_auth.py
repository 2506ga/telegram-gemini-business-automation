import os
import re
import tempfile
import unittest


_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_temp_db.close()
os.environ["DB_PATH"] = _temp_db.name
os.environ["DASHBOARD_USERNAME"] = "tester"
os.environ["DASHBOARD_PASSWORD"] = "Prueba-Temporal-123!"
os.environ["SECRET_KEY"] = "test-secret-key-only"

from dashboard import app  # noqa: E402
from database import init_db  # noqa: E402


class DashboardAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        os.unlink(_temp_db.name)

    def setUp(self):
        self.client = app.test_client()

    @staticmethod
    def csrf(response):
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        assert match
        return match.group(1).decode()

    def test_protected_dashboard_and_login_flow(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

        login_page = self.client.get("/login")
        bad_login = self.client.post(
            "/login",
            data={
                "csrf_token": self.csrf(login_page),
                "username": "tester",
                "password": "incorrecta",
            },
        )
        self.assertEqual(bad_login.status_code, 200)
        self.assertIn("incorrectos", bad_login.get_data(as_text=True))

        good_login = self.client.post(
            "/login",
            data={
                "csrf_token": self.csrf(bad_login),
                "username": "tester",
                "password": "Prueba-Temporal-123!",
            },
        )
        self.assertEqual(good_login.status_code, 302)
        self.assertEqual(good_login.location, "/")

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("Ponte Pilar", dashboard.get_data(as_text=True))

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post(
            "/login", data={"username": "tester", "password": "Prueba-Temporal-123!"}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
