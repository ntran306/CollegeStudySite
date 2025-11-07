from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup_choice/', views.signup_choice, name='signup_choice'),
    path('signup/student/', views.signup_student, name='signup_student'),
    path('signup/tutor/', views.signup_tutor, name='signup_tutor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),  # Move this BEFORE the username pattern
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/', views.profile_view, name='profile'),
    path('connect/', views.connect_list, name='connect'),
    path("connect/request/<int:user_id>/", views.connect_request, name="connect_request"),
    path("connect/requests/", views.connect_requests, name="connect_requests"),
    path("connect/requests/<int:pk>/accept/", views.connect_accept, name="connect_accept"),
    path("connect/requests/<int:pk>/decline/", views.connect_decline, name="connect_decline"),
    path("connect/requests/<int:pk>/cancel/", views.connect_cancel, name="connect_cancel"),
]