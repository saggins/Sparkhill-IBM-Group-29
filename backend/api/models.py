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