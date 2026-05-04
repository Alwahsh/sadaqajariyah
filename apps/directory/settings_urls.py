from django.urls import path

from apps.users.views import change_password_view
from . import views

urlpatterns = [
    path("", views.profile_edit_view, name="settings_profile"),
    path("password/", change_password_view, name="settings_password"),
]
