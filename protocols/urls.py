from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/<str:protocol_name>', views.dashboard, name='dashboard'),
]
