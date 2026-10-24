import datetime

from django.conf import settings
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .models import Food, MenuEntry, UserRating

LOCATION_NAME = 'The Commons'
PERIODS = dict(MenuEntry.MEAL_PERIODS)


@require_GET
def home(request):
    return redirect('menu', date=timezone.localdate().isoformat(), period='lunch')


@require_GET
def menu(request, date, period):
    if period not in PERIODS:
        raise Http404
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        raise Http404

    # Date picker submits ?date=YYYY-MM-DD; turn it into a clean URL.
    picked = request.GET.get('date')
    if picked and picked != date:
        return redirect('menu', date=picked, period=period)

    entries = (
        MenuEntry.objects
        .filter(date=day, meal_period=period)
        .select_related('food')
        .order_by('food__name')
    )

    gmail = request.session.get('gmail')
    votes = {}
    if gmail:
        food_ids = [e.food_id for e in entries]
        votes = dict(UserRating.objects.filter(gmail=gmail, food_id__in=food_ids)
                     .values_list('food_id', 'is_upvoted'))

    items = [
        {
            'food': e.food,
            'vote': None if e.food_id not in votes else 'up' if votes[e.food_id] else 'down',
        }
        for e in entries
    ]

    return render(request, 'api/menu.html', {
        'location_name': LOCATION_NAME,
        'day': day,
        'prev_day': (day - datetime.timedelta(days=1)).isoformat(),
        'next_day': (day + datetime.timedelta(days=1)).isoformat(),
        'period': period,
        'periods': MenuEntry.MEAL_PERIODS,
        'items': items,
        'gmail': gmail,
    })


def _safe_next(request):
    nxt = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return '/'


@require_POST
def vote(request):
    gmail = request.session.get('gmail')
    if not gmail:
        return HttpResponseBadRequest('Sign in before voting.')

    choice = request.POST.get('vote')
    if choice not in ('up', 'down'):
        return HttpResponseBadRequest('vote must be "up" or "down".')
    food = get_object_or_404(Food, pk=request.POST.get('food_id'))
    is_upvoted = choice == 'up'

    existing = UserRating.objects.filter(gmail=gmail, food=food).first()
    # Clicking the thumb that's already active clears the vote.
    if existing and existing.is_upvoted == is_upvoted:
        existing.delete()
    else:
        UserRating.objects.update_or_create(gmail=gmail, food=food, defaults={'is_upvoted': is_upvoted})

    return redirect(_safe_next(request))


@require_GET
def login(request):
    nxt = request.GET.get('next', '')
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = '/'
    return render(request, 'api/login.html', {
        'google_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'next': nxt,
    })


@require_POST
def google_auth(request):
    token = request.POST.get('credential')
    if not token:
        return HttpResponseBadRequest('Missing Google credential.')
    try:
        user_data = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError:
        return HttpResponseForbidden('Invalid Google credential.')
    if not user_data.get('email_verified'):
        return HttpResponseForbidden('Google account email is not verified.')

    request.session.cycle_key()
    request.session['gmail'] = user_data['email'].lower()
    return redirect(_safe_next(request))


@require_POST
def logout(request):
    request.session.flush()
    return redirect(_safe_next(request))
