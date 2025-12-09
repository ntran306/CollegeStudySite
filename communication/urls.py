from django.urls import path
from . import views

app_name = "communication"

urlpatterns = [
    path("messaging/token/", views.get_twilio_token, name="get_twilio_token"),
    path("messaging/start/<int:user_id>/", views.start_conversation, name="start_conversation"),
    path("messaging/list/", views.list_conversations, name="list_conversations"),
    path("messaging/conversation/<str:conversation_sid>/", views.conversation_view, name="conversation_view"),
    path("messaging/conversation/<str:conversation_sid>/messages/", views.get_messages, name="get_messages"),
    path("messaging/conversation/<str:conversation_sid>/other-user/", views.get_other_user, name="get_other_user"),
    path("messaging/friends/", views.get_friends_list, name="get_friends_list"),
]