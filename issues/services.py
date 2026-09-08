from rest_framework.exceptions import ValidationError
from django.utils import timezone

from .models import Issue


def change_issue_status(issue, new_status):
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

    return issue
