from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/<slug:location>/<str:date>/<slug:period>/', views.menu, name='menu'),
    path('vote/', views.vote, name='vote'),
    path('identify/', views.identify, name='identify'),
]
