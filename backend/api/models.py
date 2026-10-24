from django.db import models

# Create your models here.
class Food(models.Model):
    name = models.CharField(max_length=100)
    food_id = models.IntegerField()

class UserRatings(models.Model):
    RATING_CHOICES = [(x / 2, x / 2) for x in range(11)]

    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_ratings')
    rating = models.DecimalField(max_digits=2, decimal_places=1, choices=RATING_CHOICES)

class UserDownvotes(models.Model):
    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_downvotes')

# This part of the code is for defining food (ex: "Pizza").
# The date it is offered (ex: October 23), and the meal it is offered at (ex: lunch).

class MenuItem(models.Model):
    MEAL_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
    ]

    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    service_date = models.DateField()
    meal = models.CharField(max_length=20, choices=MEAL_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["food", "service_date", "meal"],
                name="one_food_per_menu_slot",
           )
        ]

class RecommendationDelivery(models.Model):
    gmail = models.EmailField()
    recommendation_date = models.DateField()
    subject = models.CharField(max_length=255)
    items = models.JSONField(default=list)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["gmail", "recommendation_date"],
                name="one_daily_email_per_user",
                # This makes the scheduler safe to run multiple times. 
                # A user would not receive two recommendation emails for the same day.
                            
            )
        ]