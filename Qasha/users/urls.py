from django.urls import path

from .views import (
    SignUpView,
    UserLoginView,
    logout_view,
    upgrade_account,
    request_host_verification,
    edit_profile,
)

app_name = "users"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("logout/", logout_view, name="logout"),
    path("upgrade/", upgrade_account, name="upgrade"),
    path("verify/", request_host_verification, name="request_verification"),
    path("profile/", edit_profile, name="profile"),
]
