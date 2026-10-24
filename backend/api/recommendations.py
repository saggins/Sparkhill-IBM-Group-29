# Recommendation logic


from django.db.models import Avg, Count

from .models import MenuItem, UserDownvotes, UserRatings


def get_recommendations_for_user(gmail, recommendation_date):
    downvoted_food_ids = UserDownvotes.objects.filter(
        gmail=gmail
    ).values_list("food_id", flat=True)

    rated_food_ids = UserRatings.objects.filter(
        gmail=gmail
    ).values_list("food_id", flat=True)

    menu_items = (
        MenuItem.objects
        .filter(service_date=recommendation_date)
        .exclude(food_id__in=downvoted_food_ids)
        .annotate(
            average_rating=Avg(
                "food__user_ratings__rating",
                filter=None,
            ),
            user_rating_count=Count(
                "food__user_ratings",
                filter=None,
            ),
        )
        .order_by("-average_rating", "food__name")
    )

    recommendations = []

    for item in menu_items:
        personal_rating = (
            UserRatings.objects
            .filter(gmail=gmail, food=item.food)
            .values_list("rating", flat=True)
            .first()
        )

        # Prefer foods that this user rated highly.
        if personal_rating is not None and personal_rating >= 4:
            score = 100 + float(personal_rating)
        elif personal_rating is not None:
            score = float(personal_rating)
        else:
            score = float(item.average_rating or 0)

        recommendations.append(
            {
                "food_name": item.food.name,
                "meal": item.meal,
                "score": score,
                "personal_rating": (
                    float(personal_rating)
                    if personal_rating is not None
                    else None
                ),
                "average_rating": float(item.average_rating or 0),
            }
        )

    recommendations.sort(key=lambda item: item["score"], reverse=True)

    return recommendations[:5]

