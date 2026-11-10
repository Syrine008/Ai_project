from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=["testserver"])
class ProductionAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def test_anonymous_cannot_analyze_or_email(self):
        for endpoint in ["/api/axis3-cerebellar-dysfunction/analyze/", "/api/send-report-email/"]:
            self.assertEqual(self.client.post(endpoint, {}).status_code, 403)

    def test_staff_session_requires_csrf_and_accepts_valid_token(self):
        user = get_user_model().objects.create_user(username="reviewer", password="test-only", is_staff=True)
        self.client.force_login(user)
        url = "/api/axis3-cerebellar-dysfunction/analyze/"
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        session = self.client.get("/api/session/").json()
        self.assertTrue(session["authenticated"])
        self.assertTrue(session["authenticationRequired"])
        response = self.client.post(url, {}, HTTP_X_CSRFTOKEN=session["csrfToken"])
        self.assertEqual(response.status_code, 400)  # authenticated; upload validation reached

    def test_non_staff_cannot_analyze(self):
        user = get_user_model().objects.create_user(username="nonstaff", password="test-only")
        self.client.force_login(user)
        token = self.client.get("/api/session/").json()["csrfToken"]
        self.assertEqual(self.client.post("/api/axis3-cerebellar-dysfunction/analyze/", {}, HTTP_X_CSRFTOKEN=token).status_code, 403)

    def test_session_status_does_not_cache_tokens(self):
        response = self.client.get("/api/session/")
        self.assertFalse(response.json()["authenticated"])
        self.assertIn("no-store", response["Cache-Control"])
