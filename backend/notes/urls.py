from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import NoteViewSet, ProviderProfileViewSet, TagViewSet, whoami

router = DefaultRouter()
router.register(r"notes", NoteViewSet, basename="note")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"providers", ProviderProfileViewSet, basename="provider")

urlpatterns = [
    path("user/", whoami, name="whoami"),
] + router.urls
