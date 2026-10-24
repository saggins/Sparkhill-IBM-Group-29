from django.db import models

# Create your models here.
class Food(models.Model):
    name = models.CharField(max_length=100)
    food_id = models.IntegerField()

    def __str__(self):
        return self.name

class UserRatings(models.Model):
    RATING_CHOICES = [(x / 2, x / 2) for x in range(11)]

    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_ratings')
    rating = models.DecimalField(max_digits=2, decimal_places=1, choices=RATING_CHOICES)

    def __str__(self):
        return f'{self.gmail} rated {self.food} {self.rating}'

class UserDownvotes(models.Model):
    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_downvotes')
    def __str__(self):
        return f'{self.gmail} downvoted {self.food}'

class MenuEntry(models.Model):
    MEAL_PERIODS = [
        ('breakfast', 'Breakfast'),
        ('brunch', 'Brunch'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]

    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='menu_entries')
    location = models.SlugField(default='the-commons')
    date = models.DateField()
    meal_period = models.CharField(max_length=20, choices=MEAL_PERIODS)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['food', 'location', 'date', 'meal_period'],
                name='unique_menu_entry',
            ),
        ]

    def __str__(self):
        return f'{self.food} @ {self.location} {self.date} {self.meal_period}'

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
            )
        ]
