from rest_framework.test import APITestCase
from django.urls import reverse

from issues.models import Issue
from projects.models import Project
from users.models import User
from teams.models import TeamMembership, Team


class IssuePermissionTests(APITestCase):
    def setUp(self):
        self.tanya = User.objects.create_user(
            username = 'tanya',
            password = '12345'
        )
        self.backend_team = Team.objects.create(
            name = 'backend'
        )
        self.tanya_membership = TeamMembership.objects.create(
            user = self.tanya,
            team = self.backend_team,
            role = TeamMembership.Role.OWNER
        )
        self.backend_project = Project.objects.create(
            name = 'Existing project',
            description = 'Test project',
            team = self.backend_team
        )

        self.roma = User.objects.create_user(
            username = 'roma',
            password = '12345'
        )
        self.roma_membership = TeamMembership.objects.create(
            user = self.roma,
            team = self.backend_team,
            role = TeamMembership.Role.MEMBER
        )
        self.roma_issue = Issue.objects.create(
            title = 'Existing issue',
            description = 'Test issue',
            project = self.backend_project,
            creator = self.roma
        )

        self.dima = User.objects.create_user(
            username = 'dima',
            password = '12345'
        )
        self.dima_membership = TeamMembership.objects.create(
            user = self.dima,
            team = self.backend_team,
            role = TeamMembership.Role.MANAGER
        )
        self.dima_issue = Issue.objects.create(
            title = 'Assigned issue',
            description = 'Test issue',
            project = self.backend_project,
            creator = self.dima,
            assignee = self.roma
        )
        self.foreign_issue = Issue.objects.create(
            title = 'Foreign issue',
            description = 'Test issue',
            project = self.backend_project,
            creator = self.dima,
            assignee = self.tanya
        )

        self.alex = User.objects.create_user(
            username = 'alex',
            password = '12345'
        )

    def test_member_can_create_issue(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'title': 'Backend projects issue',
            'description': 'Test issue',
            'project': self.backend_project.id
        }

        url = reverse('issue-list')

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Issue.objects.filter(
                title='Backend projects issue',
                project=self.backend_project
            ).exists()
        )

        issue = Issue.objects.get(title='Backend projects issue')
        self.assertEqual(issue.creator, self.roma)

    def test_outsider_cannot_create_issue_in_another_teams_project(self):
        self.client.force_authenticate(user=self.alex)

        data = {
            'title': 'Backend projects issue',
            'description': 'Test issue',
            'project': self.backend_project.id
        }

        url = reverse('issue-list')

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Issue.objects.filter(
                title='Backend projects issue',
                project=self.backend_project
            ).exists()
        )

    def test_member_can_modify_issue_if_hes_creator(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'title': 'Existing issue 2'
        }

        url = reverse(
            'issue-detail',
            args=[self.roma_issue.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.roma_issue.refresh_from_db()
        self.assertEqual(
            self.roma_issue.title,
            'Existing issue 2'
        )

    def test_member_can_modify_issue_if_hes_assignee_but_not_creator(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'title': 'Assigned issue 2'
        }

        url = reverse(
            'issue-detail',
            args=[self.dima_issue.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.dima_issue.refresh_from_db()
        self.assertEqual(
            self.dima_issue.title,
            'Assigned issue 2'
        )

    def test_member_cannot_modify_issue_because_hes_not_creator_or_assignee(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'title': 'Foreign issue 2'
        }

        url = reverse(
            'issue-detail',
            args=[self.foreign_issue.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 403)

        self.foreign_issue.refresh_from_db()
        self.assertEqual(
            self.foreign_issue.title,
            'Foreign issue'
        )

    def test_outsider_even_cannot_get_another_team_projects_issue(self):
        self.client.force_authenticate(user=self.alex)

        url = reverse(
            'issue-detail',
            args=[self.foreign_issue.id]
        )

        response = self.client.get(
            url,
            format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_member_cannot_delete_any_issue(self):
        self.client.force_authenticate(user=self.roma)

        url = reverse(
            'issue-detail',
            args=[self.roma_issue.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Issue.objects.filter(
                id=self.roma_issue.id
            ).exists()
        )

    def test_owner_can_delete_any_issue(self):
        self.client.force_authenticate(user=self.tanya)

        url = reverse(
            'issue-detail',
            args=[self.foreign_issue.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Issue.objects.filter(
                id=self.foreign_issue.id
            ).exists()
        )

    def test_manager_can_delete_any_issue(self):
        self.client.force_authenticate(user=self.dima)

        url = reverse(
            'issue-detail',
            args=[self.foreign_issue.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Issue.objects.filter(
                id=self.foreign_issue.id
            ).exists()
        )

    def test_cannot_assign_someone_from_another_team_as_assignee(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'assignee': self.alex.id
        }

        url = reverse(
            'issue-detail',
            args=[self.foreign_issue.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 400)

        self.foreign_issue.refresh_from_db()
        self.assertEqual(self.foreign_issue.assignee, self.tanya)
