from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from teams.models import TeamMembership

from .models import Comment
from .serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)
    allowed_roles = frozenset({TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER})

    def get_queryset(self):
        return Comment.objects.filter(
            issue__project__team__members=self.request.user
        ).order_by("id")

    def perform_create(self, serializer):
        issue = serializer.validated_data["issue"]
        team = issue.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        comment = self.get_object()
        team = comment.issue.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        if membership.role in self.allowed_roles:
            serializer.save()
            return

        if (
            membership.role == TeamMembership.Role.MEMBER
            and self.request.user != comment.author
        ):
            raise PermissionDenied(
                "У вас недостаточно прав для редактирования комментария"
            )

        serializer.save()

    def perform_destroy(self, instance):
        team = instance.issue.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        if membership.role in self.allowed_roles:
            instance.delete()
            return

        if (
            membership.role == TeamMembership.Role.MEMBER
            and self.request.user != instance.author
        ):
            raise PermissionDenied("У вас недостаточно прав для удаления комментария")

        instance.delete()
