from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("directory/", views.directory_view, name="directory"),
    path("p/<str:username>/", views.public_profile_view, name="public_profile"),
]
