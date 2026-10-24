from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/<str:date>/<slug:period>/', views.menu, name='menu'),
    path('vote/', views.vote, name='vote'),
    path('login/', views.login, name='login'),
    path('auth/google/', views.google_auth, name='google-auth'),
    path('logout/', views.logout, name='logout'),
]
