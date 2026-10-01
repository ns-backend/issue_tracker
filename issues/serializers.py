from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from teams.models import TeamMembership

from .models import Issue


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = (
            "id",
            "title",
            "description",
            "project",
            "creator",
            "assignee",
            "status",
            "priority",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        )
        read_only_fields = (
            "id",
            "creator",
            "status",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        )

    def validate(self, attrs):
        if "project" not in attrs:
            project = self.instance.project
        else:
            project = attrs["project"]

        if "assignee" not in attrs:
            return attrs

        assignee = attrs.get("assignee")

        if assignee is None:
            return attrs

        membership = TeamMembership.objects.filter(
            user=assignee, team=project.team
        ).first()

        if membership is None:
            raise serializers.ValidationError(
                "Пользователь, которого вы хотите назначить на эту задачу, не входит в команду по этому проекту"
            )

        return attrs

    def validate_project(self, value):
        if self.instance is not None and value != self.instance.project:
            raise ValidationError("Нельзя изменить проект у задачи")

        return value


class ChangeIssueStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Issue.Status.choices)
