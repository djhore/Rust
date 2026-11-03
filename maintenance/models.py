
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
from pathlib import Path

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("tenant", "Tenant"),
        ("manager", "Property Manager"),
        ("technician", "Maintenance Technician"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    apartment_number = models.CharField(max_length=50, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()

        valid_roles = {
            role for role, label in self.ROLE_CHOICES
        }

        if self.role not in valid_roles:
            raise ValidationError({
                "role": "Select a valid Rust user role."
            })

        if self.role != "tenant" and self.apartment_number:
            raise ValidationError({
                "apartment_number": (
                    "Only tenants can have an apartment number."
                )
            })

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class RoleVerificationCode(models.Model):
    ROLE_CHOICES = [
        ("tenant", "Tenant"),
        ("manager", "Property Manager"),
        ("technician", "Maintenance Technician"),
    ]

    code = models.CharField(max_length=30, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    is_used = models.BooleanField(default=False)

    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="role_verification_code",
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="issued_role_verification_codes",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        """A code is valid if it has not been used."""
        return not self.is_used

    def __str__(self):
        # Avoid displaying the actual code in the object label.
        return (
            f"{self.get_role_display()} verification code "
            f"(ID: {self.pk})"
        )



def maintenance_image_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()

    # Use a random name rather than the user's original filename.
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    if extension not in allowed_extensions:
        extension = ".jpg"

    return f"maintenance_images/{uuid.uuid4().hex}{extension}"


class MaintenanceRequest(models.Model):
    CATEGORY_CHOICES = [
        ("plumbing", "Plumbing"),
        ("electrical", "Electrical"),
        ("appliance", "Appliance"),
        ("structural", "Structural"),
        ("other", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ('cancelled', 'Cancelled'),
    ]

    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )

    apartment_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    problem_title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
    )
    description = models.TextField()

    image = models.ImageField(
        upload_to=maintenance_image_upload_path,
        blank=True,
        null=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_maintenance_requests",
    )

    date_submitted = models.DateTimeField(auto_now_add=True)
    date_assigned = models.DateTimeField(blank=True, null=True)
    date_completed = models.DateTimeField(blank=True, null=True)

    repair_notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    
    class Meta:
        indexes = [
            models.Index(
                fields=["status", "date_submitted"],
                name="maint_status_date_idx",
            ),
            models.Index(
                fields=["tenant", "date_submitted"],
                name="maint_tenant_date_idx",
            ),
            models.Index(
                fields=["assigned_technician", "status"],
                name="maint_tech_status_idx",
            ),
        ]

   
    def save(self, *args, **kwargs):
        if (
            self.status in {"assigned", "in_progress", "completed"}
            and not self.assigned_technician_id
        ):
            raise ValidationError(
                "A maintenance technician must be assigned "
                "before a request can leave the pending status."
            )

        if self.status == "pending":
            self.assigned_technician = None
            self.date_assigned = None
            self.date_completed = None

        elif self.status == "assigned":
            self.date_completed = None

            if self.date_assigned is None:
                self.date_assigned = timezone.now()

        elif self.status == "in_progress":
            self.date_completed = None

            if self.date_assigned is None:
                self.date_assigned = timezone.now()

        elif self.status == "completed":
            if self.date_assigned is None:
                self.date_assigned = timezone.now()

            if self.date_completed is None:
                self.date_completed = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.problem_title
