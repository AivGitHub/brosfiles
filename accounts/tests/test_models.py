from unittest.mock import Mock

from django.test import TransactionTestCase

from accounts.models import User


class FileCase(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create(name='user', sound='')
