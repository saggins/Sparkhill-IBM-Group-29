# Recommendation logic


from django.db.models import Avg

from .models import MenuEntry, UserRating


def get_recommendations_for_user(gmail, recommendation_date):
    downvoted_food_ids = UserRating.objects.filter(
        gmail=gmail,
        is_upvoted=False,
    ).values_list("food_id", flat=True)

    menu_entries = (
        MenuEntry.objects
        .filter(date=recommendation_date)
        .exclude(food_id__in=downvoted_food_ids)
        .annotate(
            average_rating=Avg("food__user_ratings__is_upvoted"),
        )
        .order_by("-average_rating", "food__name")
    )

    recommendations = []

    for entry in menu_entries:
        personal_rating = (
            UserRating.objects
            .filter(gmail=gmail, food=entry.food)
            .values_list("is_upvoted", flat=True)
            .first()
        )

        # Prefer foods this user explicitly upvoted.
        if personal_rating is True:
            score = 100.0
        else:
            score = float(entry.average_rating or 0)

        recommendations.append(
            {
                "food_name": entry.food.name,
                "meal": entry.meal_period,
                "score": score,
                "personal_rating": (
                    None
                    if personal_rating is None
                    else 1.0 if personal_rating else 0.0
                ),
                "average_rating": float(entry.average_rating or 0),
            }
        )

    recommendations.sort(key=lambda item: item["score"], reverse=True)

    return recommendations[:5]

