import os

from locust import HttpUser, between, task


TEST_EMAIL = os.getenv("LOAD_TEST_EMAIL", "load-test@example.com")
TEST_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "change-me")


class WhiteRockUser(HttpUser):
    wait_time = between(1, 4)
    token = None

    def on_start(self):
        response = self.client.post(
            "/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="login",
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(4)
    def health(self):
        self.client.get("/health", name="health")

    @task(2)
    def dashboard_state(self):
        if self.token:
            self.client.get("/auth/me", headers=self.headers, name="auth_me")

    @task(1)
    def ethan(self):
        if self.token:
            self.client.post(
                "/advisor/advisor",
                headers=self.headers,
                json={"message": "Quelle est mon action patrimoniale prioritaire ?"},
                name="ethan",
            )

    @task(1)
    def opportunity_search(self):
        if self.token:
            self.client.post(
                "/intelligence/opportunity-intelligence",
                headers=self.headers,
                json={"universe": "investments", "criteria": {"risk": "moderate"}},
                name="opportunity_search",
            )

    @task(1)
    def export_request(self):
        if self.token:
            self.client.post(
                "/privacy/export",
                headers=self.headers,
                json={"format": "json"},
                name="privacy_export",
            )
