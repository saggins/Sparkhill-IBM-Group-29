from django.urls import path
from .views import add_rating, rating_list

urlpatterns = [
    path('rating_list/', rating_list, name='rating-list'),
    path('add_rating/<int:pk>/', add_rating, name='add-rating'),
]