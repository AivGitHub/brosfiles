from http import HTTPStatus

from django.urls import reverse
from django.test import Client, TestCase


class HealthCase(TestCase):
    def setUp(self):
        self.url = reverse('health')
        self.client = Client()

    def test_get(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(response.content, b'')
