from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name", "description", "team")

    def validate_team(self, value):
        if self.instance is not None and value != self.instance.team:
            raise ValidationError("Нельзя изменить команду проекта")

        return value
