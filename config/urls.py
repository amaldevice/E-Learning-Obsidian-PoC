from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from courses import views as vault_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("vault/", vault_views.vault_list, name="vault-list"),
    path("vault/download/", vault_views.vault_download, name="vault-download"),
    path("courses/", include("courses.urls")),
    path("", RedirectView.as_view(pattern_name="course-list", permanent=False)),
]
