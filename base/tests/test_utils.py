from unittest.mock import Mock

from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.test import TransactionTestCase

from accounts.models import User
from base.utils import create_superuser


class BaseUtilsCase(TransactionTestCase):
    def setUp(self):
        self.apps = Mock(spec=StateApps)
        self.schema_editor = Mock(spec=DatabaseSchemaEditor)

    def tearDown(self):
        super().tearDownClass()

        User.objects.all().delete()

    def test_create_superuser(self):
        user, created = create_superuser(self.apps, self.schema_editor)
        username = user.username

        self.assertFalse(created, 'User should have been created on migration')

        User.objects.all().delete()

        self.assertFalse(User.objects.filter(username=username).exists(), 'User exists')

        user, created = create_superuser(self.apps, self.schema_editor)

        self.assertTrue(created, 'User not created')
        self.assertTrue(User.objects.filter(username=username).exists(), 'User does not exist')

        user, created = create_superuser(self.apps, self.schema_editor)

        self.assertFalse(created, 'User created, but should be already exist')
