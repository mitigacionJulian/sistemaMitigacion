from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.LoginTokenView.as_view(), name="auth-login"),
    path("refresh/", views.RefreshTokenView.as_view(), name="auth-refresh"),
    path("register/", views.register_view, name="auth-register"),
    path("logout/", views.logout_view, name="auth-logout"),
    path("me/", views.me_view, name="auth-me"),
    path(
        "password-reset/request/",
        views.password_reset_request_view,
        name="auth-password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        views.password_reset_confirm_view,
        name="auth-password-reset-confirm",
    ),
]
