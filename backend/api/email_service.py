from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import RecommendationDelivery
from .recommendations import get_recommendations_for_user


def send_daily_recommendation(gmail, recommendation_date):
    delivery, created = RecommendationDelivery.objects.get_or_create(
        gmail=gmail,
        recommendation_date=recommendation_date,
        defaults={
            "subject": "",
            "items": [],
        },
    )

    if delivery.sent_at is not None:
        return delivery

    recommendations = get_recommendations_for_user(
        gmail=gmail,
        recommendation_date=recommendation_date,
    )

    subject = f"Your menu recommendations for {recommendation_date}"

    if recommendations:
        lines = [
            "Here are your recommended items from The Commons:",
            "",
        ]

        for item in recommendations:
            lines.append(
                f"- {item['food_name']} ({item['meal']})"
            )

        body = "\n".join(lines)
    else:
        body = (
            "There are no matching recommendations "
            "for today's menu."
        )

    delivery.subject = subject
    delivery.items = recommendations

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[gmail],
        )

        email.send()

        delivery.sent_at = timezone.now()
        delivery.error = ""
        delivery.save(
            update_fields=[
                "subject",
                "items",
                "sent_at",
                "error",
            ]
        )

    except Exception as exception:
        delivery.error = str(exception)
        delivery.save(
            update_fields=[
                "subject",
                "items",
                "error",
            ]
        )
        raise

    return delivery