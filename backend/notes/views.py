from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Note, NoteTag, ProviderProfile, Tag
from .serializers import (
    NoteSerializer,
    NoteTagSerializer,
    ProviderProfileSerializer,
    TagMergeSerializer,
    TagSerializer,
    TagWriteSerializer,
)


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer

    def get_queryset(self):
        qs = (
            Note.objects.all()
            .prefetch_related("note_tags__tag")
            .distinct()
        )
        params = self.request.query_params

        tag_slugs = params.getlist("tag")
        if tag_slugs:
            for slug in tag_slugs:
                qs = qs.filter(note_tags__tag__slug=slug)
            qs = qs.distinct()

        tag_status = params.get("tag_status")
        if tag_status:
            qs = qs.filter(tag_status=tag_status)

        q = params.get("q")
        if q:
            vector = SearchVector("body_md", "title", config="english")
            query = SearchQuery(q, config="english")
            qs = (
                qs.annotate(rank=SearchRank(vector, query))
                .filter(rank__gt=0)
                .order_by("-rank", "-updated_at")
            )

        return qs

    @action(detail=True, methods=["get", "post"])
    def tags(self, request, pk=None):
        note = self.get_object()

        if request.method == "GET":
            return Response(
                {
                    "tag_status": note.tag_status,
                    "tag_error": note.tag_error,
                    "tags": NoteTagSerializer(
                        note.note_tags.all(), many=True
                    ).data,
                }
            )

        # POST: manual pin of an existing tag by slug.
        slug = (request.data or {}).get("slug")
        if not slug:
            return Response(
                {"slug": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tag = Tag.objects.get(slug=slug)
        except Tag.DoesNotExist:
            return Response(
                {"slug": ["No such tag. Tags must exist before they can be pinned."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            note_tag, created = NoteTag.objects.get_or_create(
                note=note,
                tag=tag,
                defaults={"source": NoteTag.Source.MANUAL},
            )
            if not created and note_tag.source != NoteTag.Source.MANUAL:
                note_tag.source = NoteTag.Source.MANUAL
                note_tag.save(update_fields=["source"])
            tag.usage_count = tag.note_tags.count()
            tag.save(update_fields=["usage_count"])
        note.refresh_from_db()
        return Response(
            {
                "tag_status": note.tag_status,
                "tag_error": note.tag_error,
                "tags": NoteTagSerializer(note.note_tags.all(), many=True).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path=r"tags/(?P<tag_id>[^/.]+)")
    def remove_tag(self, request, pk=None, tag_id=None):
        note = self.get_object()
        note_tag = note.note_tags.filter(tag_id=tag_id).select_related("tag").first()
        if note_tag is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tag = note_tag.tag
        note_tag.delete()
        tag.usage_count = tag.note_tags.count()
        tag.save(update_fields=["usage_count"])
        note.refresh_from_db()
        return Response(
            {
                "tag_status": note.tag_status,
                "tag_error": note.tag_error,
                "tags": NoteTagSerializer(note.note_tags.all(), many=True).data,
            }
        )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TagWriteSerializer
        return TagSerializer

    def get_queryset(self):
        return Tag.objects.all().order_by("-usage_count", "slug")

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        # Rename / change description only. Merging goes through the merge action.
        serializer.save()

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        tag = self.get_object()
        serializer = TagMergeSerializer(data=request.data, context={"tag": tag})
        serializer.is_valid(raise_exception=True)
        target = serializer.save()
        return Response(TagSerializer(target).data)


class ProviderProfileViewSet(viewsets.ModelViewSet):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_default"):
            ProviderProfile.objects.filter(is_default=True).update(is_default=False)
        serializer.save()

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default"):
            ProviderProfile.objects.filter(is_default=True).exclude(
                pk=serializer.instance.pk
            ).update(is_default=False)
        serializer.save()


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(["GET"])
@permission_classes([AllowAny])
def whoami(request):
    """Cheap auth probe for the SPA. 200 + null when anonymous."""
    if request.user.is_authenticated:
        return Response({"id": request.user.id, "username": request.user.username})
    return Response(None)
