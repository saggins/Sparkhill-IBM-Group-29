import datetime
import tempfile

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Food, MenuEntry, UserDownvotes, UserRatings

DAY = datetime.date(2026, 10, 23)


def menu_url(period='lunch', day=DAY):
    return reverse('menu', args=['the-commons', day.isoformat(), period])


class MenuViewTests(TestCase):
    def setUp(self):
        self.pizza = Food.objects.create(name='Pepperoni Pizza', food_id=1)
        self.soup = Food.objects.create(name='Tomato Soup', food_id=2)
        MenuEntry.objects.create(food=self.pizza, date=DAY, meal_period='lunch')
        MenuEntry.objects.create(food=self.soup, date=DAY, meal_period='dinner')

    def test_shows_only_that_slot(self):
        resp = self.client.get(menu_url('lunch'))
        self.assertContains(resp, 'Pepperoni Pizza')
        self.assertNotContains(resp, 'Tomato Soup')

    def test_empty_slot(self):
        resp = self.client.get(menu_url('breakfast'))
        self.assertContains(resp, 'No menu loaded for this meal.')

    def test_bad_date_or_period_404(self):
        self.assertEqual(self.client.get('/menu/the-commons/not-a-date/lunch/').status_code, 404)
        self.assertEqual(self.client.get('/menu/the-commons/2026-10-23/snack/').status_code, 404)

    def test_home_redirects_to_lunch(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith('/lunch/'))


class VoteTests(TestCase):
    def setUp(self):
        self.food = Food.objects.create(name='Pepperoni Pizza', food_id=1)
        self.gmail = 'spartan@sjsu.edu'

    def vote(self, choice):
        return self.client.post(reverse('vote'), {'food_id': self.food.pk, 'vote': choice, 'next': '/'})

    def login(self):
        self.client.post(reverse('identify'), {'gmail': self.gmail, 'next': '/'})

    def test_requires_email(self):
        self.assertEqual(self.vote('up').status_code, 400)
        self.assertFalse(UserRatings.objects.exists())

    def test_rejects_invalid_email(self):
        resp = self.client.post(reverse('identify'), {'gmail': 'nope', 'next': '/'})
        self.assertEqual(resp.status_code, 400)

    def test_up_down_toggle(self):
        self.login()
        self.vote('up')
        self.assertEqual(UserRatings.objects.get(gmail=self.gmail).rating, 5)
        self.assertFalse(UserDownvotes.objects.exists())

        self.vote('down')
        self.assertFalse(UserRatings.objects.exists())
        self.assertTrue(UserDownvotes.objects.filter(gmail=self.gmail, food=self.food).exists())

        self.vote('down')  # clicking the active thumb clears it
        self.assertFalse(UserDownvotes.objects.exists())
        self.assertFalse(UserRatings.objects.exists())

    def test_vote_state_rendered(self):
        MenuEntry.objects.create(food=self.food, date=DAY, meal_period='lunch')
        self.login()
        self.vote('up')
        resp = self.client.get(menu_url())
        self.assertContains(resp, 'aria-pressed="true" aria-label="Thumbs up"')

    def test_unsafe_next_ignored(self):
        self.login()
        resp = self.client.post(reverse('vote'), {
            'food_id': self.food.pk, 'vote': 'up', 'next': 'https://evil.example.com/',
        })
        self.assertEqual(resp.url, '/')


class SeedMenuTests(TestCase):
    def test_names_file_idempotent(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt') as f:
            f.write('Pepperoni Pizza\n  pepperoni   pizza \nCaesar Salad\n\n')
            f.flush()
            args = ['seed_menu', '--names-file', f.name, '--date', '2026-10-23', '--period', 'lunch']
            call_command(*args, stdout=open('/dev/null', 'w'))
            call_command(*args, stdout=open('/dev/null', 'w'))

        self.assertEqual(Food.objects.count(), 2)
        self.assertEqual(MenuEntry.objects.count(), 2)
        self.assertEqual(sorted(Food.objects.values_list('food_id', flat=True)), [1, 2])

    def test_dry_run_writes_nothing(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt') as f:
            f.write('Pepperoni Pizza\n')
            f.flush()
            call_command('seed_menu', '--names-file', f.name, '--period', 'lunch', '--dry-run',
                         stdout=open('/dev/null', 'w'))
        self.assertFalse(Food.objects.exists())
