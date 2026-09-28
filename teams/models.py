from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="TeamMembership")


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        MANAGER = "manager", "Менеджер"
        MEMBER = "member", "Сотрудник"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    role = models.CharField(max_length=7, choices=Role.choices)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["user", "team"], name="unique_user_in_team")
        ]
