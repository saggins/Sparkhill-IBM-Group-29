from django.db import models

# Create your models here.
class Food(models.Model):
    name = models.CharField(max_length=100, unique=True)
    food_id = models.IntegerField(unique=True)

    class Meta:
        verbose_name_plural = 'Food'
        ordering = ['name', 'food_id']

    def __str__(self):
        return self.name

class UserRating(models.Model):
    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_ratings')
    is_upvoted = models.BooleanField(default=True, db_default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['gmail', 'food'], name='unique_gmail_food_constraint'),
        ]

    def __str__(self):
        return f'{self.gmail} {"upvoted" if self.is_upvoted else "downvoted"} {self.food}'

class MenuEntry(models.Model):
    MEAL_PERIODS = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]

    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='menu_entries')
    date = models.DateField()
    meal_period = models.CharField(max_length=20, choices=MEAL_PERIODS)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['food', 'date', 'meal_period'],
                name='unique_menu_entry',
            ),
        ]

    def __str__(self):
        return f'{self.food} {self.date} {self.meal_period}'
