from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Team, TeamMembership
from .serializers import TeamSerializer, TeamMembershipSerializer


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all().order_by('id')
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        with transaction.atomic():
            team = serializer.save()
            TeamMembership.objects.create(
                user = self.request.user,
                team = team,
                role = TeamMembership.Role.OWNER
            )

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        team = self.get_object()

        if not TeamMembership.objects.filter(user=request.user, team=team).exists():
            raise PermissionDenied('У вас недостаточно прав для выполнения этого действия')

        if request.method == 'GET':

            members = TeamMembership.objects.filter(team=team)

            serializer = TeamMembershipSerializer(
                members,
                many=True
            )

            return Response(serializer.data)

        elif request.method == 'POST':
            membership = TeamMembership.objects.get(user=request.user, team=team)

            if membership.role != TeamMembership.Role.OWNER:
                raise PermissionDenied('У вас недостаточно прав для выполнения этого действия')

            serializer = TeamMembershipSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            new_role = serializer.validated_data['role']
            if new_role == TeamMembership.Role.OWNER:
                raise ValidationError('Недопустимое значение роли')

            new_user = serializer.validated_data['user']
            if TeamMembership.objects.filter(user=new_user, team=team).exists():
                raise ValidationError('Пользователь уже состоит в этой команде')

            serializer.save(team=team)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
