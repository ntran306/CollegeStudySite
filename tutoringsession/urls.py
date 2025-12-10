from django.urls import path
from . import views

app_name = "tutoringsession"

urlpatterns = [
    # STUDENT VIEW
    path("", views.index, name="index"),
    # TUTOR DASHBOARD
    path("dashboard/", views.tutor_dashboard, name="dashboard"),
    # CREATE
    path("create/", views.create_session, name="create"),
    # DETAIL
    path("<int:session_id>/", views.session_detail, name="detail"),
    # EDIT
    path("<int:session_id>/edit/", views.edit_session, name="edit"),
    # DELETE
    path("<int:session_id>/delete/", views.delete_session, name="delete"),
    # REQUEST
    path("<int:session_id>/request/", views.request_session, name="request"),
    # FRIENDS
    path("friends/", views.friends_sessions, name="friends_sessions"),
    # TUTOR SEARCH
    path("search-students/", views.search_students, name="search_students"),
    # APPROVE / DECLINE 
    path("request/<int:request_id>/approve/", views.approve_request, name="approve_request"),
    path("request/<int:request_id>/decline/", views.decline_request, name="decline_request"),
    # MY REQUESTS
    path("my-requests/", views.my_requests, name="my_requests"),
    # CANCEL REQUEST
    path("request/<int:request_id>/cancel/", views.cancel_request, name="cancel_request"),

]
