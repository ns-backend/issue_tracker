from rest_framework import serializers

from .models import IssueHistory


class IssueHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueHistory
        fields = [
            'id',
            'user',
            'field',
            'old_value',
            'new_value',
            'created_at'
            ]
        read_only_fields = [
            'id',
            'user',
            'field',
            'old_value',
            'new_value',
            'created_at'
            ]
