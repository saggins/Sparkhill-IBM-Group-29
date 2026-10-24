import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from api.models import Food, MenuEntry

MENU_URL = 'https://dineoncampus.com/SJSU/whats-on-the-menu/the-commons/{date}/{period}'


def normalize(name):
    # Same whitespace rule as lib.food_recommender, but keep the original casing for display.
    return ' '.join(name.split())


class Command(BaseCommand):
    help = 'Load one meal period of The Commons menu into MenuEntry.'

    def add_arguments(self, parser):
        parser.add_argument('--date', default=None, help='YYYY-MM-DD (default: today)')
        parser.add_argument(
            '--period', required=True, choices=[p for p, _ in MenuEntry.MEAL_PERIODS]
        )
        parser.add_argument(
            '--names-file', help='Read food names from this file (one per line) instead of scraping.'
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            date = (
                datetime.date.fromisoformat(options['date'])
                if options['date']
                else datetime.date.today()
            )
        except ValueError:
            raise CommandError(f"Bad --date {options['date']!r}, expected YYYY-MM-DD.")

        period = options['period']
        names = self.load_names(options['names_file'], date, period)

        # De-dupe case-insensitively while keeping first-seen order.
        unique = {}
        for raw in names:
            name = normalize(raw)
            if name:
                unique.setdefault(name.lower(), name)
        names = list(unique.values())

        if options['dry_run']:
            for name in names:
                self.stdout.write(f'  {name}')
            self.stdout.write(f'Would save {len(names)} items for {date} {period}.')
            return

        created_foods = created_entries = 0
        with transaction.atomic():
            next_food_id = (Food.objects.aggregate(m=Max('food_id'))['m'] or 0) + 1
            for name in names:
                food = Food.objects.filter(name__iexact=name).first()
                if food is None:
                    food = Food.objects.create(name=name, food_id=next_food_id)
                    next_food_id += 1
                    created_foods += 1
                _, created = MenuEntry.objects.get_or_create(
                    food=food, date=date, meal_period=period
                )
                created_entries += created

        self.stdout.write(self.style.SUCCESS(
            f'{date} {period}: {len(names)} items '
            f'({created_foods} new foods, {created_entries} new menu entries).'
        ))

    def load_names(self, names_file, date, period):
        if names_file:
            with open(names_file) as f:
                return f.read().splitlines()

        try:
            from lib.scraper import scrape_menu
        except ImportError:
            raise CommandError(
                'lib.scraper.scrape_menu not found. Use --names-file until the scraper lands.'
            )
        url = MENU_URL.format(date=date.isoformat(), period=period)
        self.stdout.write(f'Scraping {url}')
        return scrape_menu(url)
