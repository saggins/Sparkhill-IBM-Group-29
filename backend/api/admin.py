from django.contrib import admin

from .models import Food, MenuEntry, UserDownvotes, UserRatings

# Register your models here.
admin.site.register(Food)
admin.site.register(UserRatings)
admin.site.register(UserDownvotes)

@admin.register(MenuEntry)
class MenuEntryAdmin(admin.ModelAdmin):
    list_display = ['food', 'location', 'date', 'meal_period']
    list_filter = ['location', 'meal_period', 'date']
