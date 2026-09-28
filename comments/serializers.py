from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "text", "issue", "author", "created_at", "updated_at")
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def validate_issue(self, value):
        if self.instance is not None and value != self.instance.issue:
            raise ValidationError("Нельзя изменить задачу у комментария")

        return value
