from django.urls import path
from .consumers import ProctoringConsumer

websocket_urlpatterns = [
    path("ws/proctoring", ProctoringConsumer.as_asgi()),
]