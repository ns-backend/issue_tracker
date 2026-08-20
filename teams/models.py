from django.db import models
from django.conf import settings


class Team(models.Model):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='TeamMembership')


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Владелец'
        MANAGER = 'manager', 'Менеджер'
        MEMBER = 'member', 'Сотрудник'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=7, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'team'],
                name='unique_user_in_team'
            )
        ]
