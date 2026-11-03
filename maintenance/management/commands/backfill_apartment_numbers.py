
from django.core.management.base import BaseCommand
from django.db.models import Q

from maintenance.models import MaintenanceRequest


class Command(BaseCommand):
    help = (
        "Fill blank maintenance-request apartment numbers "
        "from the tenant's profile."
    )

    def handle(self, *args, **options):
        requests = (
            MaintenanceRequest.objects
            .filter(Q(apartment_number__isnull=True) | Q(apartment_number=""))
            .select_related("tenant")
        )

        updated = 0
        skipped = 0

        for maintenance_request in requests.iterator():
            try:
                apartment_number = (
                    maintenance_request.tenant.userprofile.apartment_number
                )
            except Exception:
                skipped += 1
                continue

            if apartment_number:
                maintenance_request.apartment_number = apartment_number
                maintenance_request.save(
                    update_fields=["apartment_number"]
                )
                updated += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated} maintenance request(s)."
            )
        )

        self.stdout.write(
            f"Skipped {skipped} request(s) with no available apartment number."
        )
