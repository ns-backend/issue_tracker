from rest_framework.test import APITestCase
from django.urls import reverse
from django.utils import timezone

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


class IssueStatusTests(APITestCase):
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
        self.new_issue = Issue.objects.create(
            title = 'Status test',
            project = self.backend_project,
            creator = self.tanya
        )
        self.in_progress_issue = Issue.objects.create(
            title = 'Status test',
            project = self.backend_project,
            creator = self.tanya,
            status = Issue.Status.IN_PROGRESS,
            started_at = timezone.now()
        )
        self.done_issue = Issue.objects.create(
            title = 'Status test',
            project = self.backend_project,
            creator = self.tanya,
            status = Issue.Status.DONE,
            completed_at = timezone.now()
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

        self.roma = User.objects.create_user(
            username='roma',
            password='12345'
        )
        self.roma_membership = TeamMembership.objects.create(
            user=self.roma,
            team=self.backend_team,
            role=TeamMembership.Role.MEMBER
        )
        self.roma_new_issue = Issue.objects.create(
            title='Membership test',
            project=self.backend_project,
            creator=self.roma
        )
        self.roma_assigned_issue = Issue.objects.create(
            title='Membership test',
            project=self.backend_project,
            creator=self.tanya,
            assignee=self.roma,
        )

        self.foreign_new_issue = Issue.objects.create(
            title='Membership test',
            project=self.backend_project,
            creator=self.tanya,
        )

    def test_new_can_change_to_in_progress(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.new_issue.refresh_from_db()
        self.assertEqual(
            self.new_issue.status,
            Issue.Status.IN_PROGRESS
        )
        self.assertIsNotNone(self.new_issue.started_at)

    def test_in_progress_can_change_to_done(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.DONE
        }

        url = reverse(
            'issue-change-status',
            args=[self.in_progress_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.in_progress_issue.refresh_from_db()
        self.assertEqual(
            self.in_progress_issue.status,
            Issue.Status.DONE
        )
        self.assertIsNotNone(self.in_progress_issue.completed_at)

    def test_done_can_change_to_in_progress(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.done_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.done_issue.refresh_from_db()
        self.assertEqual(
            self.done_issue.status,
            Issue.Status.IN_PROGRESS
        )
        self.assertIsNone(self.done_issue.completed_at)

    def test_in_progress_can_change_to_new(self):
        self.client.force_authenticate(user=self.tanya)

        old_started_at = self.in_progress_issue.started_at

        data = {
            'status': Issue.Status.NEW
        }

        url = reverse(
            'issue-change-status',
            args=[self.in_progress_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.in_progress_issue.refresh_from_db()
        self.assertEqual(
            self.in_progress_issue.status,
            Issue.Status.NEW
        )
        self.assertEqual(
            self.in_progress_issue.started_at,
            old_started_at
        )

    def test_new_cannot_change_to_done(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.DONE
        }

        url = reverse(
            'issue-change-status',
            args=[self.new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 400)

        self.new_issue.refresh_from_db()
        self.assertEqual(
            self.new_issue.status,
            Issue.Status.NEW
        )
        self.assertIsNone(self.new_issue.completed_at)

    def test_done_cannot_change_to_new(self):
        self.client.force_authenticate(user=self.tanya)

        old_completed_at = self.done_issue.completed_at

        data = {
            'status': Issue.Status.NEW
        }

        url = reverse(
            'issue-change-status',
            args=[self.done_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 400)

        self.done_issue.refresh_from_db()
        self.assertEqual(
            self.done_issue.status,
            Issue.Status.DONE
        )
        self.assertEqual(
            old_completed_at,
            self.done_issue.completed_at
        )

    def test_new_cannot_change_to_new(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.NEW
        }

        url = reverse(
            'issue-change-status',
            args=[self.new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 400)

        self.new_issue.refresh_from_db()
        self.assertEqual(
            self.new_issue.status,
            Issue.Status.NEW
        )
        self.assertIsNone(self.new_issue.started_at)

    def test_cannot_change_to_invalid_status(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': 'abracadabra'
        }

        url = reverse(
            'issue-change-status',
            args=[self.new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 400)

        self.new_issue.refresh_from_db()
        self.assertEqual(
            self.new_issue.status,
            Issue.Status.NEW
        )
        self.assertIsNone(self.new_issue.started_at)
        self.assertIsNone(self.new_issue.completed_at)

    def test_member_can_change_status_issue_when_his_creator(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.roma_new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.roma_new_issue.refresh_from_db()
        self.assertEqual(
            self.roma_new_issue.status,
            Issue.Status.IN_PROGRESS
        )

    def test_member_cannot_change_status_issue_when_his_not_creator_and_not_assignee(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.foreign_new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 403)

        self.foreign_new_issue.refresh_from_db()
        self.assertEqual(
            self.foreign_new_issue.status,
            Issue.Status.NEW
        )
        self.assertIsNone(self.foreign_new_issue.started_at)

    def test_owner_can_change_any_issue_of_his_team(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.foreign_new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.foreign_new_issue.refresh_from_db()
        self.assertEqual(
            self.foreign_new_issue.status,
            Issue.Status.IN_PROGRESS
        )
        self.assertIsNotNone(self.foreign_new_issue.started_at)

    def test_manager_can_change_any_issue_of_his_team(self):
        self.client.force_authenticate(user=self.dima)

        data = {
            'status': Issue.Status.IN_PROGRESS
        }

        url = reverse(
            'issue-change-status',
            args=[self.roma_new_issue.id]
        )

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.roma_new_issue.refresh_from_db()
        self.assertEqual(
            self.roma_new_issue.status,
            Issue.Status.IN_PROGRESS
        )
        self.assertIsNotNone(self.roma_new_issue.started_at)
