import datetime
import tempfile
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Food, MenuEntry, UserRating

DAY = datetime.date(2026, 10, 23)


def menu_url(period='lunch', day=DAY):
    return reverse('menu', args=[day.isoformat(), period])


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
        self.assertEqual(self.client.get('/menu/not-a-date/lunch/').status_code, 404)
        self.assertEqual(self.client.get('/menu/2026-10-23/snack/').status_code, 404)

    def test_home_redirects_to_lunch(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith('/lunch/'))

    @mock.patch('api.views.should_recommend')
    def test_no_recommendations_without_rating_history(self, recommend):
        self.assertNotContains(self.client.get(menu_url()), 'You might like this')
        session = self.client.session
        session['gmail'] = 'spartan@sjsu.edu'
        session.save()
        self.assertNotContains(self.client.get(menu_url()), 'You might like this')
        recommend.assert_not_called()

    @mock.patch('api.views.should_recommend')
    def test_recommendations_use_only_current_users_full_history(self, recommend):
        gmail = 'spartan@sjsu.edu'
        session = self.client.session
        session['gmail'] = gmail
        session.save()
        # Soup is on a different meal's menu, but still informs recommendations.
        UserRating.objects.create(gmail=gmail, food=self.soup, is_upvoted=True)
        UserRating.objects.create(gmail='other@sjsu.edu', food=self.pizza, is_upvoted=False)
        recommend.return_value = True

        resp = self.client.get(menu_url())
        recommend.assert_called_once_with('Pepperoni Pizza', [(gmail, 'Tomato Soup', True)], gmail)
        self.assertContains(resp, 'You might like this', count=1)
        self.assertContains(resp, 'bg-green-50')

        recommend.return_value = False
        resp = self.client.get(menu_url())
        self.assertNotContains(resp, 'You might like this')
        self.assertNotContains(resp, 'bg-green-50')


class VoteTests(TestCase):
    def setUp(self):
        self.food = Food.objects.create(name='Pepperoni Pizza', food_id=1)
        self.gmail = 'spartan@sjsu.edu'

    def vote(self, choice):
        return self.client.post(reverse('vote'), {'food_id': self.food.pk, 'vote': choice, 'next': '/'})

    def login(self):
        with mock.patch('api.views.id_token.verify_oauth2_token',
                        return_value={'email': self.gmail, 'email_verified': True}):
            self.client.post(reverse('google-auth'), {'credential': 'tok', 'next': '/'})

    def test_requires_email(self):
        self.assertEqual(self.vote('up').status_code, 400)
        self.assertFalse(UserRating.objects.exists())

    def test_rejects_invalid_token(self):
        with mock.patch('api.views.id_token.verify_oauth2_token', side_effect=ValueError):
            resp = self.client.post(reverse('google-auth'), {'credential': 'bad', 'next': '/'})
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn('gmail', self.client.session)

    def test_rejects_unverified_email(self):
        with mock.patch('api.views.id_token.verify_oauth2_token',
                        return_value={'email': self.gmail, 'email_verified': False}):
            resp = self.client.post(reverse('google-auth'), {'credential': 'tok', 'next': '/'})
        self.assertEqual(resp.status_code, 403)

    def test_login_then_logout(self):
        self.login()
        self.assertEqual(self.client.session['gmail'], self.gmail)
        self.client.post(reverse('logout'), {'next': '/'})
        self.assertNotIn('gmail', self.client.session)

    def test_login_page_renders_button(self):
        resp = self.client.get(reverse('login'), {'next': 'https://evil.example.com/'})
        self.assertContains(resp, 'g_id_signin')
        self.assertContains(resp, 'name="next" value="/"')

    def test_up_down_toggle(self):
        self.login()
        self.vote('up')
        self.assertTrue(UserRating.objects.get(gmail=self.gmail, food=self.food).is_upvoted)

        self.vote('down')
        self.assertFalse(UserRating.objects.get(gmail=self.gmail, food=self.food).is_upvoted)

        self.vote('down')  # clicking the active thumb clears it
        self.assertFalse(UserRating.objects.exists())

    @mock.patch('api.views.should_recommend', return_value=True)
    def test_vote_state_rendered(self, recommend):
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
