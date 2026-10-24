from django.contrib import admin

from .models import Food, MenuEntry, RecommendationDelivery, UserRating

# Register your models here.
admin.site.register(Food)
admin.site.register(UserRating)
admin.site.register(RecommendationDelivery)

@admin.register(MenuEntry)
class MenuEntryAdmin(admin.ModelAdmin):
    list_display = ['food', 'date', 'meal_period']
    list_filter = ['meal_period', 'date']
