# Recommendation logic


from django.db.models import Avg

from .models import MenuEntry, UserDownvotes, UserRatings


def get_recommendations_for_user(gmail, recommendation_date):
    downvoted_food_ids = UserDownvotes.objects.filter(
        gmail=gmail
    ).values_list("food_id", flat=True)

    menu_entries = (
        MenuEntry.objects
        .filter(
            location="the-commons",
            date=recommendation_date,
        )
        .exclude(food_id__in=downvoted_food_ids)
        .annotate(
            average_rating=Avg("food__user_ratings__rating"),
        )
        .order_by("-average_rating", "food__name")
    )

    recommendations = []

    for entry in menu_entries:
        personal_rating = (
            UserRatings.objects
            .filter(gmail=gmail, food=entry.food)
            .values_list("rating", flat=True)
            .first()
        )

        # Prefer foods that this user rated highly.
        if personal_rating is not None and personal_rating >= 4:
            score = 100 + float(personal_rating)
        elif personal_rating is not None:
            score = float(personal_rating)
        else:
            score = float(entry.average_rating or 0)

        recommendations.append(
            {
                "food_name": entry.food.name,
                "meal": entry.meal_period,
                "score": score,
                "personal_rating": (
                    float(personal_rating)
                    if personal_rating is not None
                    else None
                ),
                "average_rating": float(entry.average_rating or 0),
            }
        )

    recommendations.sort(key=lambda item: item["score"], reverse=True)

    return recommendations[:5]

