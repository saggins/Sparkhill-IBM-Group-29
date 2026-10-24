import datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .models import Food, MenuEntry, UserDownvotes, UserRatings

LOCATIONS = {'the-commons': 'The Commons'}
PERIODS = dict(MenuEntry.MEAL_PERIODS)
THUMBS_UP_RATING = 5.0


@require_GET
def home(request):
    return redirect('menu', location='the-commons', date=timezone.localdate().isoformat(), period='lunch')


@require_GET
def menu(request, location, date, period):
    if location not in LOCATIONS or period not in PERIODS:
        raise Http404
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError:
        raise Http404

    # Date picker submits ?date=YYYY-MM-DD; turn it into a clean URL.
    picked = request.GET.get('date')
    if picked and picked != date:
        return redirect('menu', location=location, date=picked, period=period)

    entries = (
        MenuEntry.objects
        .filter(location=location, date=day, meal_period=period)
        .select_related('food')
        .order_by('food__name')
    )

    gmail = request.session.get('gmail')
    liked, disliked = set(), set()
    if gmail:
        food_ids = [e.food_id for e in entries]
        liked = set(UserRatings.objects.filter(gmail=gmail, food_id__in=food_ids, rating__gte=3)
                    .values_list('food_id', flat=True))
        disliked = set(UserDownvotes.objects.filter(gmail=gmail, food_id__in=food_ids)
                       .values_list('food_id', flat=True))

    items = [
        {
            'food': e.food,
            'vote': 'up' if e.food_id in liked else 'down' if e.food_id in disliked else None,
        }
        for e in entries
    ]

    return render(request, 'api/menu.html', {
        'location': location,
        'location_name': LOCATIONS[location],
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
        return HttpResponseBadRequest('Set your email before voting.')

    choice = request.POST.get('vote')
    if choice not in ('up', 'down'):
        return HttpResponseBadRequest('vote must be "up" or "down".')
    food = get_object_or_404(Food, pk=request.POST.get('food_id'))

    ratings = UserRatings.objects.filter(gmail=gmail, food=food)
    downvotes = UserDownvotes.objects.filter(gmail=gmail, food=food)
    # Clicking the thumb that's already active clears the vote.
    already = ratings.filter(rating__gte=3).exists() if choice == 'up' else downvotes.exists()

    ratings.delete()
    downvotes.delete()
    if not already:
        if choice == 'up':
            UserRatings.objects.create(gmail=gmail, food=food, rating=THUMBS_UP_RATING)
        else:
            UserDownvotes.objects.create(gmail=gmail, food=food)

    return redirect(_safe_next(request))


@require_POST
def identify(request):
    gmail = request.POST.get('gmail', '').strip().lower()
    if gmail:
        try:
            validate_email(gmail)
        except ValidationError:
            return HttpResponseBadRequest('Enter a valid email address.')
        request.session['gmail'] = gmail
    else:
        request.session.pop('gmail', None)
    return redirect(_safe_next(request))
