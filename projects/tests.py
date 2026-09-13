from rest_framework.test import APITestCase
from django.urls import reverse
from projects.models import Project

from users.models import User
from teams.models import TeamMembership, Team


class ProjectPermissionTests(APITestCase):
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

        self.roma = User.objects.create_user(
            username = 'roma',
            password = '12345'
        )
        self.roma_membership = TeamMembership.objects.create(
            user = self.roma,
            team = self.backend_team,
            role = TeamMembership.Role.MEMBER
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

        self.alex = User.objects.create_user(
            username = 'alex',
            password = '12345'
        )
        self.backend_project = Project.objects.create(
            name = 'Existing project',
            description = 'Test project',
            team = self.backend_team
        )

    def test_owner_can_create_project(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'name': 'Backend API',
            'description': 'Test project',
            'team': self.backend_team.id
        }

        url = reverse('project-list')

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Project.objects.filter(
                name='Backend API',
                team = self.backend_team
            ).exists()
        )

    def test_member_cannot_create_project(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'name': 'Backend API',
            'description': 'Test project',
            'team': self.backend_team.id
        }

        url = reverse('project-list')

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Project.objects.filter(
                name='Backend API',
                team=self.backend_team
            ).exists()
        )

    def test_manager_can_create_project(self):
        self.client.force_authenticate(user=self.dima)

        data = {
            'name': 'Backend API',
            'description': 'Test project',
            'team': self.backend_team.id
        }

        url = reverse('project-list')

        response = self.client.post(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Project.objects.filter(
                name='Backend API',
                team=self.backend_team
            ).exists()
        )

    def test_outsider_cannot_see_another_teams_project(self):
        self.client.force_authenticate(user=self.alex)

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.get(
            url,
            format='json'
        )

        self.assertEqual(response.status_code, 404)

    def test_member_can_see_project_own_team(self):
        self.client.force_authenticate(user=self.roma)

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.get(
            url,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

    def test_member_cannot_change_project(self):
        self.client.force_authenticate(user=self.roma)

        data = {
            'name': 'Existing project 2'
        }

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 403)

        self.backend_project.refresh_from_db()
        self.assertEqual(
            self.backend_project.name,
            'Existing project'
        )

    def test_owner_can_change_project(self):
        self.client.force_authenticate(user=self.tanya)

        data = {
            'name': 'Existing project 2'
        }

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.backend_project.refresh_from_db()
        self.assertEqual(
            self.backend_project.name,
            'Existing project 2'
        )

    def test_manager_can_change_project(self):
        self.client.force_authenticate(user=self.dima)

        data = {
            'name': 'Existing project 2'
        }

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.patch(
            url,
            data,
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.backend_project.refresh_from_db()
        self.assertEqual(
            self.backend_project.name,
            'Existing project 2'
        )

    def test_member_cannot_delete_project(self):
        self.client.force_authenticate(user=self.roma)

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Project.objects.filter(
                id=self.backend_project.id
            ).exists()
        )

    def test_owner_can_delete_project(self):
        self.client.force_authenticate(user=self.tanya)

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Project.objects.filter(
                id=self.backend_project.id
            ).exists()
        )

    def test_manager_can_delete_project(self):
        self.client.force_authenticate(user=self.dima)

        url = reverse(
            'project-detail',
            args=[self.backend_project.id]
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Project.objects.filter(
                id=self.backend_project.id
            ).exists()
        )
