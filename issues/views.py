from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from teams.models import TeamMembership

from .models import Issue
from .serializers import IssueSerializer
from .services import change_issue_status


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    allowed_roles = {TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER}
    allowed_ordering = {
        'id',
        '-id',
        'created_at',
        '-created_at',
        'updated_at',
        '-updated_at',
        'priority',
        '-priority'
        }

    def get_queryset(self):
        status = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        search = self.request.query_params.get('search')
        ordering = self.request.query_params.get('ordering')

        queryset = Issue.objects.filter(
            project__team__members = self.request.user
        )

        if status is not None:
            if status not in Issue.Status.values:
                raise ValidationError('Недопустимый статус')

            queryset = queryset.filter(status = status)

        if priority is not None:
            if priority not in Issue.Priority.values:
                raise ValidationError('Недопустимый приоритет')

            queryset = queryset.filter(priority = priority)

        if search is not None:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        if ordering is not None:
            if ordering not in self.allowed_ordering:
                raise ValidationError('Недопустимый порядок')

            return queryset.order_by(ordering)

        return queryset.order_by('id')

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

        issue = change_issue_status(issue=issue, new_status=new_status)

        serializer = self.get_serializer(issue)
        return Response(serializer.data)
