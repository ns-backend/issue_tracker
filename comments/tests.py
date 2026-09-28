from django.urls import reverse
from rest_framework.test import APITestCase

from comments.models import Comment
from issues.models import Issue
from projects.models import Project
from teams.models import Team, TeamMembership
from users.models import User


class CommentPermissionTests(APITestCase):
    def setUp(self):
        self.tanya = User.objects.create_user(username="tanya", password="12345")
        self.backend_team = Team.objects.create(name="backend")
        self.tanya_membership = TeamMembership.objects.create(
            user=self.tanya, team=self.backend_team, role=TeamMembership.Role.OWNER
        )
        self.backend_project = Project.objects.create(
            name="Existing project", description="Test project", team=self.backend_team
        )
        self.new_issue = Issue.objects.create(
            title="Comment test", project=self.backend_project, creator=self.tanya
        )
        self.in_progress_issue = Issue.objects.create(
            title="Comment test",
            project=self.backend_project,
            creator=self.tanya,
            status=Issue.Status.IN_PROGRESS,
        )
        self.tanya_comment = Comment.objects.create(
            text="Tanya comment", issue=self.new_issue, author=self.tanya
        )

        self.dima = User.objects.create_user(username="dima", password="12345")
        self.dima_membership = TeamMembership.objects.create(
            user=self.dima, team=self.backend_team, role=TeamMembership.Role.MANAGER
        )

        self.roma = User.objects.create_user(username="roma", password="12345")
        self.roma_membership = TeamMembership.objects.create(
            user=self.roma, team=self.backend_team, role=TeamMembership.Role.MEMBER
        )
        self.roma_comment = Comment.objects.create(
            text="Roma comment", issue=self.new_issue, author=self.roma
        )

        self.alex = User.objects.create_user(username="alex", password="12345")

    def test_member_can_create_comment(self):
        self.client.force_authenticate(user=self.roma)

        data = {"text": "Test comment", "issue": self.new_issue.id}

        url = reverse("comment-list")

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Comment.objects.filter(text="Test comment", issue=self.new_issue).exists()
        )

        comment = Comment.objects.get(text="Test comment", issue=self.new_issue)

        self.assertEqual(comment.author, self.roma)

    def test_outsider_cannot_create_comment_in_another_team_projects_issue(self):
        self.client.force_authenticate(user=self.alex)

        data = {"text": "Test comment", "issue": self.new_issue.id}

        url = reverse("comment-list")

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Comment.objects.filter(text="Test comment", issue=self.new_issue).exists()
        )

    def test_member_can_change_only_his_own_comment(self):
        self.client.force_authenticate(user=self.roma)

        data = {"text": "Roma comment 2"}

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.roma_comment.refresh_from_db()

        self.assertEqual(self.roma_comment.text, "Roma comment 2")

    def test_member_cannot_change_comment_if_it_is_not_him_own(self):
        self.client.force_authenticate(user=self.roma)

        data = {"text": "Tanya comment 2"}

        url = reverse("comment-detail", args=[self.tanya_comment.id])

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, 403)

        self.tanya_comment.refresh_from_db()

        self.assertEqual(self.tanya_comment.text, "Tanya comment")

    def test_owner_can_change_any_comment_of_his_team(self):
        self.client.force_authenticate(user=self.tanya)

        data = {"text": "Roma comment 2"}

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.roma_comment.refresh_from_db()

        self.assertEqual(self.roma_comment.text, "Roma comment 2")

    def test_manager_can_change_any_comment_of_his_team(self):
        self.client.force_authenticate(user=self.dima)

        data = {"text": "Roma comment 2"}

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.roma_comment.refresh_from_db()

        self.assertEqual(self.roma_comment.text, "Roma comment 2")

    def test_member_can_delete_his_own_comment(self):
        self.client.force_authenticate(user=self.roma)

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Comment.objects.filter(id=self.roma_comment.id).exists())

    def test_member_cannot_delete_comment_if_it_isnt_him(self):
        self.client.force_authenticate(user=self.roma)

        url = reverse("comment-detail", args=[self.tanya_comment.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(id=self.tanya_comment.id).exists())

    def test_owner_can_delete_any_comment_his_own_team(self):
        self.client.force_authenticate(user=self.tanya)

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Comment.objects.filter(id=self.roma_comment.id).exists())

    def test_manager_can_delete_any_comment_if_he_in_the_team(self):
        self.client.force_authenticate(user=self.dima)

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Comment.objects.filter(id=self.roma_comment.id).exists())

    def test_outsider_cannot_get_comment_in_another_team(self):
        self.client.force_authenticate(user=self.alex)

        url = reverse("comment-detail", args=[self.roma_comment.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_cannot_change_issue_associated_with_existing_comment(self):
        self.client.force_authenticate(user=self.tanya)

        data = {"issue": self.in_progress_issue.id}

        url = reverse("comment-detail", args=[self.tanya_comment.id])

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, 400)

        self.tanya_comment.refresh_from_db()

        self.assertEqual(self.tanya_comment.issue, self.new_issue)
