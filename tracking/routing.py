from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/tracking/bus/(?P<bus_id>\w+)/$', consumers.BusTrackingConsumer.as_asgi()),
    re_path(r'ws/tracking/student/(?P<student_id>\w+)/$', consumers.StudentTrackingConsumer.as_asgi()),
]