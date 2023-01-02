import datetime
from typing import Optional, Tuple

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
import jwt

from accounts.models import User
from base.exceptions import FatalSignatureError, SignatureExpiredError


DEFAULT_JWT_EXPIRATION_TIME: int = 60 * 60


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


def generate_jwt_signature(
        payload: dict,
        expiration_time: Optional[int] = DEFAULT_JWT_EXPIRATION_TIME,
        algorithm: Optional[str] = 'HS256'
) -> str:
    """Generates encoded JWT.

    JWT does not imply encryption, but payload signed with secret key,
    so later signature can be verified, until ``expiration_time`` is not expired.

    Args:
        payload (dict): Payload to be encoded.
        expiration_time (int, optional): After expiration time JWT signature can't be verified.
        algorithm (str, optional): With this algorithm payload will be signed.

    Returns:
        str: JWT signature.
    """
    cleaned_payload: dict = dict()

    if expiration_time is None:
        expiration_time = DEFAULT_JWT_EXPIRATION_TIME

    for key, value in payload.items():
        cleaned_payload.update({key: value})

    cleaned_payload.update(
        {
            'exp': datetime.datetime.now() + datetime.timedelta(seconds=expiration_time)
        }
    )

    return jwt.encode(cleaned_payload, settings.BF_JWT_AUTH_KEY, algorithm=algorithm)


def decode_jwt_signature(token, algorithms=None):
    if algorithms is None:
        algorithms = ['HS256']

    try:
        return jwt.decode(token, settings.BF_JWT_AUTH_KEY, algorithms=algorithms)
    except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidSignatureError):
        raise FatalSignatureError()
    except jwt.exceptions.ExpiredSignatureError:
        raise SignatureExpiredError()
