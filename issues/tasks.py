from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Issue


logger = get_task_logger(__name__)


@shared_task
def notify_issue_created(issue_id):
    try:
        issue = Issue.objects.get(id=issue_id)
    except Issue.DoesNotExist:
        return

    logger.info("Issue #%s created: %s", issue.id, issue.title)
