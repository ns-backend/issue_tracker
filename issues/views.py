from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from history.models import IssueHistory
from history.serializers import IssueHistorySerializer
from teams.models import TeamMembership

from .models import Issue
from .serializers import IssueSerializer
from .services import change_issue_status
from .tasks import notify_issue_created


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    permission_classes = (IsAuthenticated,)
    allowed_roles = frozenset({TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER})
    allowed_ordering = frozenset(
        {
            "id",
            "-id",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "priority",
            "-priority",
        }
    )

    def get_queryset(self):
        status = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering")

        queryset = Issue.objects.filter(project__team__members=self.request.user)

        if status is not None:
            if status not in Issue.Status.values:
                raise ValidationError("Недопустимый статус")

            queryset = queryset.filter(status=status)

        if priority is not None:
            if priority not in Issue.Priority.values:
                raise ValidationError("Недопустимый приоритет")

            queryset = queryset.filter(priority=priority)

        if search is not None:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        if ordering is not None:
            if ordering not in self.allowed_ordering:
                raise ValidationError("Недопустимый порядок")

            return queryset.order_by(ordering)

        return queryset.order_by("id")

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=project.team
        ).first()

        if membership is None:
            raise PermissionDenied(
                "Чтобы создать задачу, вам нужно состоять в этой команде"
            )

        with transaction.atomic():
            issue = serializer.save(creator=self.request.user)

            transaction.on_commit(lambda: notify_issue_created.delay(issue.id))

    def perform_update(self, serializer):
        issue = serializer.instance
        team = issue.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        if (
            membership.role not in self.allowed_roles
            and membership.role != TeamMembership.Role.MEMBER
        ):
            raise PermissionDenied("У вас недостаточно прав для обновления задачи")

        if (
            membership.role == TeamMembership.Role.MEMBER
            and self.request.user != issue.creator
            and self.request.user != issue.assignee
        ):
            raise PermissionDenied("У вас недостаточно прав для обновления задачи")

        tracked_fields = {
            "title": "title",
            "description": "description",
            "priority": "priority",
            "assignee": "assignee_id",
        }

        old_values = {}

        for field, attribute in tracked_fields.items():
            old_values[field] = getattr(issue, attribute)

        with transaction.atomic():
            updated_issue = serializer.save()

            for field, attribute in tracked_fields.items():
                old_value = old_values[field]
                new_value = getattr(updated_issue, attribute)

                if old_value != new_value:
                    IssueHistory.objects.create(
                        issue=updated_issue,
                        user=self.request.user,
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                    )

    def perform_destroy(self, instance):
        team = instance.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        if membership.role not in self.allowed_roles:
            raise PermissionDenied("У вас недостаточно прав для удаления задачи")

        instance.delete()

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        issue = self.get_object()
        team = issue.project.team

        membership = TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).first()

        if membership is None:
            raise PermissionDenied("Вы не состоите в этой команде")

        if (
            membership.role not in self.allowed_roles
            and membership.role != TeamMembership.Role.MEMBER
        ):
            raise PermissionDenied("У вас недостаточно прав для смены статуса задачи")

        if (
            membership.role == TeamMembership.Role.MEMBER
            and self.request.user != issue.creator
            and self.request.user != issue.assignee
        ):
            raise PermissionDenied("У вас недостаточно прав для смены статуса задачи")

        new_status = request.data.get("status")

        issue = change_issue_status(
            issue=issue, new_status=new_status, user=request.user
        )

        serializer = self.get_serializer(issue)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        issue = self.get_object()
        history = issue.history.all()

        serializer = IssueHistorySerializer(history, many=True)

        return Response(serializer.data)
