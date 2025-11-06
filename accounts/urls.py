from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup_choice/', views.signup_choice, name='signup_choice'),
    path('signup/student/', views.signup_student, name='signup_student'),
    path('signup/tutor/', views.signup_tutor, name='signup_tutor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
]
