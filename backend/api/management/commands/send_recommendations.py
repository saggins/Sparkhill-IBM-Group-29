from django.core.management.base import BaseCommand
from django.utils import timezone

from api.email_service import send_daily_recommendation
from api.models import UserRating


class Command(BaseCommand):
    help = "Send daily recommendation emails"

    def handle(self, *args, **options):
        recommendation_date = timezone.localdate()

        users = UserRating.objects.values_list(
            "gmail",
            flat=True,
        )

        users = set(users)

        if not users:
            self.stdout.write("No users found.")
            return

        for gmail in sorted(users):
            try:
                send_daily_recommendation(
                    gmail=gmail,
                    recommendation_date=recommendation_date,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {gmail}"
                    )
                )

            except Exception as exception:
                self.stderr.write(
                    self.style.ERROR(
                        f"Failed for {gmail}: {exception}"
                    )
                )
