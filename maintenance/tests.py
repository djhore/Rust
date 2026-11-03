
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import UserProfile, MaintenanceRequest


class RoleAccessTests(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(
            username="test_tenant",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.tenant,
            role="tenant",
        )

        self.manager = User.objects.create_user(
            username="test_manager",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.manager,
            role="manager",
        )

        self.technician = User.objects.create_user(
            username="test_technician",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.technician,
            role="technician",
        )

    def test_logged_out_user_is_redirected_from_tenant_page(self):
        response = self.client.get(reverse("my_requests"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_tenant_can_access_tenant_requests(self):
        self.client.force_login(self.tenant)

        response = self.client.get(reverse("my_requests"))

        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_access_tenant_requests(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("my_requests"))

        self.assertEqual(response.status_code, 403)

    def test_technician_cannot_access_tenant_requests(self):
        self.client.force_login(self.technician)

        response = self.client.get(reverse("my_requests"))

        self.assertEqual(response.status_code, 403)

    def test_tenant_cannot_access_manager_requests(self):
        self.client.force_login(self.tenant)

        response = self.client.get(reverse("manager_requests"))

        self.assertEqual(response.status_code, 403)

    def test_manager_can_access_manager_requests(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("manager_requests"))

        self.assertEqual(response.status_code, 200)

    def test_tenant_cannot_access_technician_requests(self):
        self.client.force_login(self.tenant)

        response = self.client.get(reverse("technician_requests"))

        self.assertEqual(response.status_code, 403)

    def test_technician_can_access_technician_requests(self):
        self.client.force_login(self.technician)

        response = self.client.get(reverse("technician_requests"))

        self.assertEqual(response.status_code, 200)


class TechnicianWorkflowTests(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(
            username="workflow_technician",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.technician,
            role="technician",
        )

        self.other_technician = User.objects.create_user(
            username="other_technician",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.other_technician,
            role="technician",
        )

        self.tenant = User.objects.create_user(
            username="workflow_tenant",
            password="TestPassword!456",
        )
        UserProfile.objects.create(
            user=self.tenant,
            role="tenant",
            apartment_number="A12",
        )

        self.maintenance_request = MaintenanceRequest.objects.create(
            tenant=self.tenant,
            problem_title="Leaking kitchen tap",
            category="plumbing",
            description="The kitchen tap is leaking.",
            status="assigned",
            assigned_technician=self.technician,
        )

        self.client.force_login(self.technician)

        self.update_url = reverse(
            "technician_update_request",
            args=[self.maintenance_request.pk],
        )

        self.detail_url = reverse(
            "technician_request_detail",
            args=[self.maintenance_request.pk],
        )

    def test_technician_can_save_progress_note_without_completing(self):
        response = self.client.post(
            self.update_url,
            {
                "repair_notes": "Inspected the leaking tap.",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.maintenance_request.refresh_from_db()

        self.assertEqual(
            self.maintenance_request.status,
            "assigned",
        )
        self.assertEqual(
            self.maintenance_request.repair_notes,
            "Inspected the leaking tap.",
        )
        self.assertIsNone(
            self.maintenance_request.date_completed,
        )

    def test_technician_can_start_maintenance(self):
        response = self.client.post(
            self.update_url,
            {
                "status": "in_progress",
                "repair_notes": "Started inspecting the tap.",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.maintenance_request.refresh_from_db()

        self.assertEqual(
            self.maintenance_request.status,
            "in_progress",
        )
        self.assertIsNone(
            self.maintenance_request.date_completed,
        )

    def test_request_cannot_be_completed_without_repair_notes(self):
        self.maintenance_request.status = "in_progress"
        self.maintenance_request.save()

        response = self.client.post(
            self.update_url,
            {
                "status": "completed",
                "repair_notes": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.maintenance_request.refresh_from_db()

        self.assertEqual(
            self.maintenance_request.status,
            "in_progress",
        )
        self.assertIsNone(
            self.maintenance_request.date_completed,
        )

    def test_technician_can_complete_request_with_repair_notes(self):
        self.maintenance_request.status = "in_progress"
        self.maintenance_request.save()

        response = self.client.post(
            self.update_url,
            {
                "status": "completed",
                "repair_notes": "Replaced the worn washer and tested the tap.",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.maintenance_request.refresh_from_db()

        self.assertEqual(
            self.maintenance_request.status,
            "completed",
        )
        self.assertEqual(
            self.maintenance_request.repair_notes,
            "Replaced the worn washer and tested the tap.",
        )
        self.assertIsNotNone(
            self.maintenance_request.date_completed,
        )

    def test_technician_cannot_update_another_technicians_request(self):
        self.maintenance_request.assigned_technician = (
            self.other_technician
        )
        self.maintenance_request.save()

        response = self.client.post(
            self.update_url,
            {
                "status": "in_progress",
                "repair_notes": "Attempted unauthorised update.",
            },
        )

        self.assertEqual(response.status_code, 404)

        self.maintenance_request.refresh_from_db()

        self.assertEqual(
            self.maintenance_request.status,
            "assigned",
        )
        self.assertEqual(
            self.maintenance_request.repair_notes,
            "",
        )

    def test_technician_cannot_open_another_technicians_request(self):
        self.maintenance_request.assigned_technician = (
            self.other_technician
        )
        self.maintenance_request.save()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 404)
