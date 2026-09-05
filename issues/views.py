from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from teams.models import TeamMembership

from .models import Issue
from .serializers import IssueSerializer


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    allowed_roles = {TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER}

    def get_queryset(self):
        return Issue.objects.filter(
            project__team__members = self.request.user
        ).order_by('id')

    def perform_create(self, serializer):
        project = serializer.validated_data['project']

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team = project.team
        ).first()

        if membership is None:
            raise PermissionDenied('Чтобы создать задачу, вам нужно состоять в этой команде')

        serializer.save(creator=self.request.user)

    def perform_update(self, serializer):
        issue = self.get_object()
        team = issue.project.team

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team = team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if membership.role in self.allowed_roles:
            serializer.save()
            return

        if membership.role == TeamMembership.Role.MEMBER:
            if self.request.user != issue.creator and self.request.user != issue.assignee:
                raise PermissionDenied('У вас недостаточно прав для обновления задачи')

        serializer.save()

    def perform_destroy(self, instance):
        team = instance.project.team

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team = team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if membership.role not in self.allowed_roles:
            raise PermissionDenied('У вас недостаточно прав для удаления задачи')

        instance.delete()

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        issue = self.get_object()
        team = issue.project.team

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team = team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if (
            membership.role not in self.allowed_roles
            and membership.role != TeamMembership.Role.MEMBER):
            raise PermissionDenied('У вас недостаточно прав для смены статуса задачи')

        if membership.role == TeamMembership.Role.MEMBER:
            if self.request.user != issue.creator and self.request.user != issue.assignee:
                raise PermissionDenied('У вас недостаточно прав для смены статуса задачи')

        new_status = request.data.get('status')
        allowed_transitions = {
            Issue.Status.NEW: {Issue.Status.IN_PROGRESS},
            Issue.Status.IN_PROGRESS: {Issue.Status.NEW, Issue.Status.DONE},
            Issue.Status.DONE: {Issue.Status.IN_PROGRESS}
        }

        if new_status not in Issue.Status.values:
            raise ValidationError('Недопустимый статус')

        if new_status not in allowed_transitions[issue.status]:
            raise ValidationError('Недопустимый переход статуса')

        if (
            issue.status == Issue.Status.NEW
            and new_status == Issue.Status.IN_PROGRESS
            and issue.started_at is None
            ):
            issue.started_at = timezone.now()

        elif issue.status == Issue.Status.IN_PROGRESS and new_status == Issue.Status.DONE:
            issue.completed_at = timezone.now()

        elif issue.status == Issue.Status.DONE and new_status == Issue.Status.IN_PROGRESS:
            issue.completed_at = None

        issue.status = new_status
        issue.save()

        serializer = self.get_serializer(issue)
        return Response(serializer.data)
