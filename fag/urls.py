"""
URL configuration for fag project.
"""
from django.contrib import admin # type: ignore
from django.urls import include, path # type: ignore
from django.conf.urls.i18n import i18n_patterns # type: ignore
from django.conf import settings # type: ignore
from django.conf.urls.static import static # type: ignore
from django.contrib.auth import views as auth_views # type: ignore
from django.views.generic import RedirectView # type: ignore


urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", RedirectView.as_view(url="/fr/", permanent=False)),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
]

urlpatterns += i18n_patterns(
    path("", include("gestion.urls")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
