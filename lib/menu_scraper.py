"""Fetch food names from the SJSU Dine On Campus menu API.

The public Dine On Campus page is a JavaScript application.  This module
therefore calls the JSON API used by that page instead of trying to parse the
initial HTML shell.

No HTML parser is required.  The only inputs are a date and one of the three
supported meal names; The Commons is always used as the location.
"""

from __future__ import annotations

from datetime import date as Date
import json
import re
from typing import Any, Callable
from urllib.parse import urlencode

import certifi
import requests


LOCATION = "The Commons"
_API_BASE_URL = "https://apiv4.dineoncampus.com"

# This is the public API identifier for The Commons at San Jose State.
_LOCATION_ID = "5b50c589f3eeb609b36a87eb"

_VALID_MEALS = frozenset({"breakfast", "lunch", "dinner"})
_JSONFetcher = Callable[[str, float], Any]


class MenuScrapeError(RuntimeError):
    """Raised when the menu API response cannot be used."""


def scrape_menu(
    menu_date: str | Date,
    meal: str,
    *,
    timeout: float = 30,
    fetch_json: _JSONFetcher | None = None,
) -> dict[str, list[str]]:
    """Return food names grouped by restaurant for The Commons.

    Args:
        menu_date: Menu date as ``YYYY-MM-DD`` or a ``datetime.date`` object.
        meal: One of ``"breakfast"``, ``"lunch"``, or ``"dinner"``.
        timeout: Maximum seconds for each API request.
        fetch_json: Optional test hook accepting ``(url, timeout)`` and
            returning decoded JSON.  Normal callers should omit it.

    Returns:
        A dictionary whose keys are restaurant/category names and whose values
        are food names in the order returned by the API.  Portions, calories,
        descriptions, and dietary information are never returned.

    Raises:
        ValueError: If the date or meal is invalid.
        HTTPError/URLError: If the API request fails.
        MenuScrapeError: If no matching meal or menu categories are returned.
    """

    date_text = _format_date(menu_date)
    meal_text = _normalise_meal(meal)
    if fetch_json is not None:
        get_json = fetch_json
    else:
        session = requests.Session()
        session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            }
        )
        session.get(
            "https://dineoncampus.com/sjsu/",
            timeout=timeout,
        )
        get_json = lambda url, request_timeout: _fetch_json(
            url,
            request_timeout,
            session,
        )

    periods_url = _api_url(
        f"/locations/{_LOCATION_ID}/periods/", date=date_text
    )
    periods_payload = get_json(periods_url, timeout)
    period_id = _find_period_id(periods_payload, meal_text)
    if period_id is None:
        raise MenuScrapeError(
            f'No "{meal_text}" period was returned for {LOCATION} on {date_text}.'
        )

    menu_url = _api_url(
        f"/locations/{_LOCATION_ID}/menu",
        date=date_text,
        period=period_id,
    )
    return parse_menu_payload(get_json(menu_url, timeout))


def parse_menu_payload(payload: Any) -> dict[str, list[str]]:
    """Extract restaurant names and food names from a menu API response.

    The current response is shaped like ``{"period": {"categories": [...]}}``.
    A couple of harmless wrappers are also accepted so the parser remains
    useful if the API adds a top-level ``data`` or ``menu`` object.
    """

    data = _unwrap_payload(payload)
    if isinstance(data, dict) and isinstance(data.get("menu"), dict):
        data = data["menu"]
    period = data.get("period") if isinstance(data, dict) else None
    if not isinstance(period, dict):
        period = data

    categories = period.get("categories") if isinstance(period, dict) else None
    if not isinstance(categories, list):
        raise MenuScrapeError("The menu API response has no categories list.")

    restaurants: dict[str, list[str]] = {}
    for category in categories:
        if not isinstance(category, dict):
            continue

        restaurant = _first_text(category, "name", "title", "label")
        if not restaurant:
            continue

        items = category.get("items", [])
        if not isinstance(items, list):
            items = []

        foods: list[str] = []
        for item in items:
            if isinstance(item, str):
                food_name = item.strip()
            elif isinstance(item, dict):
                food_name = _first_text(item, "name", "title", "label")
            else:
                food_name = ""

            if food_name:
                foods.append(food_name)

        restaurants.setdefault(restaurant, []).extend(foods)

    if not restaurants:
        raise MenuScrapeError("The menu API response contains no restaurant categories.")
    return restaurants


def _fetch_json(
    url: str,
    timeout: float,
    session: requests.Session,
) -> Any:
    response = session.get(
        url,
        timeout=timeout,
        headers={
            "Origin": "https://dineoncampus.com",
            "Referer": "https://dineoncampus.com/sjsu/",
        },
        verify=certifi.where(),
    )

    if response.status_code >= 400:
        detail = response.text[:300].replace("\n", " ").strip()
        raise MenuScrapeError(
            f"Menu API returned HTTP {response.status_code}: {detail}"
        )

    return response.json()


def _api_url(path: str, **params: str) -> str:
    return f"{_API_BASE_URL}{path}?{urlencode(params)}"


def _find_period_id(payload: Any, meal: str) -> str | None:
    data = _unwrap_payload(payload)
    periods = data.get("periods") if isinstance(data, dict) else data
    if not isinstance(periods, list):
        return None

    for period in periods:
        if not isinstance(period, dict):
            continue
        names = (
            period.get("name"),
            period.get("slug"),
            period.get("title"),
        )
        if any(_normalise_label(value) == meal for value in names if value):
            period_id = period.get("id")
            if period_id is not None:
                return str(period_id)
    return None


def _unwrap_payload(payload: Any) -> Any:
    data = payload
    while isinstance(data, dict) and isinstance(data.get("data"), (dict, list)):
        data = data["data"]
    return data


def _first_text(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _format_date(menu_date: str | Date) -> str:
    if isinstance(menu_date, Date):
        return menu_date.isoformat()
    if not isinstance(menu_date, str):
        raise ValueError("menu_date must be a YYYY-MM-DD string or datetime.date.")

    try:
        parsed = Date.fromisoformat(menu_date)
    except ValueError as exc:
        raise ValueError("menu_date must use YYYY-MM-DD format.") from exc
    return parsed.isoformat()


def _normalise_meal(meal: str) -> str:
    if not isinstance(meal, str):
        raise ValueError('meal must be one of "breakfast", "lunch", or "dinner".')
    meal_text = _normalise_label(meal)
    if meal_text not in _VALID_MEALS:
        allowed = ", ".join(sorted(_VALID_MEALS))
        raise ValueError(f"meal must be one of: {allowed}.")
    return meal_text


def _normalise_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


__all__ = [
    "LOCATION",
    "MenuScrapeError",
    "parse_menu_payload",
    "scrape_menu",
]
