from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Project
from .serializers import ProjectSerializer
from teams.models import TeamMembership


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    allowed_roles = {TeamMembership.Role.OWNER, TeamMembership.Role.MANAGER}

    def get_queryset(self):
        return Project.objects.filter(
            team__members = self.request.user,
        ).order_by('id')

    def perform_create(self, serializer):
        team = serializer.validated_data['team']

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team=team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if membership.role not in self.allowed_roles:
            raise PermissionDenied('У вас недостаточно прав для создания проекта')

        serializer.save()

    def perform_update(self, serializer):
        project = self.get_object()
        team = project.team

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team=team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if membership.role not in self.allowed_roles:
            raise PermissionDenied('У вас недостаточно прав для обновления проекта')

        serializer.save()

    def perform_destroy(self, instance):
        team = instance.team

        membership = TeamMembership.objects.filter(
            user = self.request.user,
            team=team
        ).first()

        if membership is None:
            raise PermissionDenied('Вы не состоите в этой команде')

        if membership.role not in self.allowed_roles:
            raise PermissionDenied('У вас недостаточно прав для удаления проекта')

        instance.delete()
