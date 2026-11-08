from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    NoteViewSet,
    ProviderProfileViewSet,
    TagViewSet,
    login_view,
    logout_view,
    whoami,
)

router = DefaultRouter()
router.register(r"notes", NoteViewSet, basename="note")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"providers", ProviderProfileViewSet, basename="provider")

urlpatterns = [
    path("user/", whoami, name="whoami"),
    path("auth/login/", login_view, name="login"),
    path("auth/logout/", logout_view, name="logout"),
] + router.urls
