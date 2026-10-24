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
    RATING_CHOICES = [(x / 2, x / 2) for x in range(11)]

    gmail = models.EmailField()
    food = models.ForeignKey(Food, on_delete=models.PROTECT, related_name='user_ratings')
    is_upvoted = models.BooleanField(default=True, db_default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['gmail', 'food'],
                name='unique_gmail_food_constraint'
            )
        ]

    def __str__(self):
        return f"{self.gmail} {self.food} rating"