from django.urls import path
from . import views

app_name = 'classes'

urlpatterns = [
    path('api/create/', views.create_class, name='create_class'),
]