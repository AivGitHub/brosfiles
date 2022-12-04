from typing import Tuple

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

from accounts.models import User


def create_superuser(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> Tuple[User, bool]:
    """ Dynamically creates an admin user as part of a migration.
    """
    if settings.TRAMPOLINE_CI:
        admin_username = 'admin'
        admin_password = 'test'
    else:
        admin_username = settings.ENV.get_value('BF_ADMIN_USERNAME')
        admin_password = settings.ENV.get_value('BF_ADMIN_PASSWORD')

    with transaction.atomic():
        try:
            user = User.objects.create_superuser(admin_username, password=admin_password.strip())
        except IntegrityError:
            # User already exists
            pass
        else:
            return user, True

    user = User.objects.get(username=admin_username)

    return user, False
