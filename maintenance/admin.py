from django.contrib import admin

from .models import UserProfile, MaintenanceRequest, RoleVerificationCode


@admin.register(RoleVerificationCode)
class RoleVerificationCodeAdmin(admin.ModelAdmin):

    list_display = (
        'code',
        'role',
        'is_used',
        'used_by',
        'created_at',
    )

    list_filter = (
        'role',
        'is_used',
    )

    search_fields = (
        'code',
        'used_by__username',
    )


admin.site.register(UserProfile)
admin.site.register(MaintenanceRequest)