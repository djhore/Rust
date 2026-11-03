import secrets

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, MaintenanceRequest, RoleVerificationCode


# Allow administrators to manage users, but not delete their accounts.
admin.site.unregister(User)


@admin.register(User)
class RustUserAdmin(BaseUserAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

class RoleVerificationCodeAdminForm(forms.ModelForm):
    class Meta:
        model = RoleVerificationCode
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["code"].required = False

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip()

        if not code:
            return code

        if (
            RoleVerificationCode.objects
            .filter(code=code)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "This verification code already exists."
            )

        return code

@admin.register(RoleVerificationCode)
class RoleVerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
    "code",
    "role",
    "is_used",
    "used_by",
    "issued_by",
    "created_at",
    )

    list_filter = ("role", "is_used")
    search_fields = ("code", "used_by__username")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        # Once a code has been used, lock all its fields.
        if obj is not None and obj.is_used:
            readonly.extend(
                field.name
                for field in obj._meta.fields
                if field.name not in readonly
            )

        return tuple(dict.fromkeys(readonly))

    def has_delete_permission(self, request, obj=None):
        # Do not allow used codes to be deleted.
        if obj is not None and obj.is_used:
            return False

        return super().has_delete_permission(request, obj)

    form = RoleVerificationCodeAdminForm

    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.code:
                while True:
                    generated_code = secrets.token_urlsafe(18)

                    if not RoleVerificationCode.objects.filter(
                        code=generated_code
                    ).exists():
                        obj.code = generated_code
                        break

            if not obj.issued_by_id:
                obj.issued_by = request.user

        super().save_model(request, obj, form, change)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "phone_number",
        "apartment_number",
    )
    list_filter = ("role",)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
    )

    def has_delete_permission(self, request, obj=None):
        return False

    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(
            super().get_readonly_fields(request, obj)
        )

        if (
            obj is not None
            and obj.role == "technician"
            and obj.user.assigned_maintenance_requests.exists()
            and "role" not in readonly_fields
        ):
            readonly_fields.append("role")

        return readonly_fields

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        "problem_title",
        "tenant",
        "category",
        "priority",
        "status",
        "assigned_technician",
        "date_submitted",
    )
    list_filter = ("status", "priority", "category")
    search_fields = (
        "problem_title",
        "tenant__username",
        "assigned_technician__username",
    )
    ordering = ("-date_submitted",)
