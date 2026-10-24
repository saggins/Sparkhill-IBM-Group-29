from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Food, UserRating
from .serializers import FoodSerializer, UserRatingSerializer

import os
from google.oauth2 import id_token
from google.auth.transport import requests


@api_view(['GET'])
def rating_list(request):
    token = request.POST['credential']
    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID']
        )
    except ValueError:
        return Response(status=status.HTTP_403_FORBIDDEN)

    gmail = user_data.email
    user_ratings = UserRating.objects.filter(gmail=gmail)
    serializer = UserRatingSerializer(user_ratings, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def add_rating(request, pk):
    token = request.POST['credential']
    try:
        user_data = id_token.verify_oauth2_token(
            token, requests.Request(), os.environ['GOOGLE_OAUTH_CLIENT_ID']
        )
    except ValueError:
        return Response(status=status.HTTP_403_FORBIDDEN)

    gmail = user_data.email
    food = get_object_or_404(Food, pk=pk)

    try:
        rating = UserRating.objects.get(gmail=gmail, food=food)
        serializer = UserRatingSerializer(rating, data=request.data)
    except UserRating.DoesNotExist:
        serializer = UserRatingSerializer(data=request.data)
    
    serializer.is_valid(raise_exception=True)
    serializer.save(gmail=gmail)
    
    return Response(data=serializer.data, status=status.HTTP_201_CREATED)