from django.urls import path

from .api_views import (
    AgentCapabilitiesAPIView,
    AgentCatalogAPIView,
    AgentConversationCreateAPIView,
    AgentConversationDetailAPIView,
    AgentConversationMessageAPIView,
    AgentLearningExampleReviewAPIView,
    AgentMemoryAPIView,
)

app_name = "ia-api"

urlpatterns = [
    path("agents/", AgentCatalogAPIView.as_view(), name="agent-catalog"),
    path("agents/<slug:slug>/capabilities/", AgentCapabilitiesAPIView.as_view(), name="agent-capabilities"),
    path("agents/<slug:slug>/memory/", AgentMemoryAPIView.as_view(), name="agent-memory"),
    path("conversations/", AgentConversationCreateAPIView.as_view(), name="conversation-create"),
    path("conversations/<uuid:conversation_uuid>/", AgentConversationDetailAPIView.as_view(), name="conversation-detail"),
    path(
        "conversations/<uuid:conversation_uuid>/messages/",
        AgentConversationMessageAPIView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<uuid:conversation_uuid>/learning-examples/<int:pk>/review/",
        AgentLearningExampleReviewAPIView.as_view(),
        name="learning-example-review",
    ),
]
