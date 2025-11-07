from django.urls import path
from . import views

app_name = "tutoringsession"

urlpatterns = [
    path("", views.index, name="index"),
    path("friends-sessions/", views.friends_sessions, name="friends_sessions"),
    path("<int:session_id>/request/", views.request_session, name="request_session"),
    path("search-students/", views.search_students, name="search_students"),
]