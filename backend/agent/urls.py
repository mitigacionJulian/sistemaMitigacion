from django.urls import path

from . import views

urlpatterns = [
    path("agent/info/", views.agent_info_view, name="agent-info"),
    path("agent/chat/", views.agent_chat_view, name="agent-chat"),
]
