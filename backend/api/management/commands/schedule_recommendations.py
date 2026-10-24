import datetime
import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Run send_recommendations every day at a fixed local time"

    def add_arguments(self, parser):
        parser.add_argument(
            "--at",
            default=os.environ.get("RECOMMENDATION_SEND_TIME", "20:00"),
            help="HH:MM in TIME_ZONE (default: $RECOMMENDATION_SEND_TIME or 20:00)",
        )

    def handle(self, *args, **options):
        try:
            send_at = datetime.time.fromisoformat(options["at"])
        except ValueError:
            raise CommandError(f"Bad --at {options['at']!r}, expected HH:MM.")

        while True:
            now = timezone.localtime()
            next_run = now.replace(
                hour=send_at.hour,
                minute=send_at.minute,
                second=0,
                microsecond=0,
            )

            if next_run <= now:
                next_run += datetime.timedelta(days=1)

            self.stdout.write(f"Next recommendation run at {next_run}")
            time.sleep((next_run - now).total_seconds())

            # send_recommendations skips users already emailed today, so a
            # restart near send time can't double-send.
            try:
                call_command("send_recommendations")
            except Exception as exception:
                self.stderr.write(
                    self.style.ERROR(f"Recommendation run failed: {exception}")
                )
