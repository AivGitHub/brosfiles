from hashlib import sha256
from pathlib import Path
import secrets

from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import magic

from accounts.managers import UserManager
from accounts.utils import file_upload_path, get_uuid_hex


MAGIC_MIME = magic.Magic(mime=True)
DEFAULT_MAX_FILE_SIZE: int = 100 * 2**20


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _('username'),
        max_length=64,
        help_text=_('150 characters or fewer. Letters and digits only.'),
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
        null=False,
        blank=False,
        unique=True
    )
    first_name = models.CharField(
        _('First name'),
        max_length=150,
        null=False,
        blank=False
    )
    last_name = models.CharField(
        _('Last name'),
        max_length=50,
        null=False,
        blank=False
    )
    email = models.EmailField(
        _('Email address'),
        max_length=254,
        error_messages={
            'unique': _('A user with that email already exists.'),
        },
        default=None,
        null=True,
        blank=True
    )
    is_staff = models.BooleanField(
        _('Staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('Active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active. '
                    'Unselect this instead of deleting accounts.'),
    )
    date_joined = models.DateTimeField(
        _('Date joined'),
        default=timezone.now
    )
    public_key = models.TextField(
        _('Public key'),
        max_length=2056,
        null=True,
        blank=True
    )
    max_file_size = models.IntegerField(
        _('Maximum file size'),
        default=DEFAULT_MAX_FILE_SIZE,
        null=True,
        blank=True
    )

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self) -> str:
        return self.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self) -> str:
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'

        if self.first_name:
            return self.first_name

        if self.last_name:
            return self.last_name

        return self.username

    def email_user(self, subject, message, from_email=None, **kwargs) -> None:
        send_mail(subject, message, from_email, [self.email], **kwargs)


def get_upload_hex():
    """Generates UUID4 hex for upload_hex field."""
    return get_uuid_hex(File, 'upload_hex')


def get_url_path():
    """Generates unique hash for file."""
    return '%s%s' % (get_uuid_hex(File, 'url_path'), secrets.token_hex(nbytes=16))


class File(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True
    )
    file = models.FileField(
        _('File'),
        max_length=512,
        upload_to=file_upload_path,
        null=True,
        blank=True
    )
    sha256 = models.CharField(
        _('File sha256 hash'),
        max_length=64,
        editable=False,
        null=False,
        blank=False
    )
    original_full_name = models.CharField(
        _('Original full name'),
        max_length=256,
        editable=False,
        null=False,
        blank=False
    )
    original_name = models.CharField(
        _('Original name'),
        max_length=128,
        editable=False,
        null=True,
        blank=True
    )
    original_extension = models.CharField(
        _('Original extension'),
        max_length=64,
        editable=False,
        null=True,
        blank=True
    )
    content_type = models.CharField(
        _('Content type'),
        max_length=64,
        editable=False,
        null=False,
        blank=False
    )
    is_private = models.BooleanField(
        _('Is private'),
        default=False
    )
    is_encrypted = models.BooleanField(
        _('Is encrypted'),
        editable=False,
        default=False
    )
    size = models.IntegerField(
        _('Size'),
        editable=False,
        null=True,
        blank=True
    )
    exif = models.TextField(
        _('Exif data'),
        max_length=65535,
        editable=False,
        null=True,
        blank=True
    )
    ip = models.CharField(
        _('IP'),
        max_length=16,
        editable=False,
        null=False,
        blank=False
    )
    upload_hex = models.CharField(
        _('Upload hex'),
        max_length=32,
        default=get_upload_hex,
        editable=False,
        null=False,
        blank=False,
        unique=True
    )
    url_path = models.CharField(
        _('URL Path'),
        max_length=64,
        default=get_url_path,
        editable=False,
        null=False,
        blank=False,
        unique=True
    )

    def __str__(self):
        return self.sha256[:8]

    def save(self, *args, **kwargs):
        fake: bool = kwargs.pop('fake', False)
        original_full_name: str = kwargs.pop('original_full_name', None)

        self.set_name_attrs(original_full_name)

        if fake is False:
            self.set_file_attrs()
        else:
            self.set_fake_file_attrs()

        super().save(*args, **kwargs)

    def set_name_attrs(self, original_full_name):
        if self.original_full_name and original_full_name is None:
            return

        if original_full_name is not None:
            self.original_full_name = original_full_name
        else:
            self.original_full_name = self.file.name

        # Avoid using absolute paths, because absolute paths can be not supported by backends.
        file_path = Path(self.original_full_name)

        self.original_name = file_path.stem
        self.original_extension = file_path.suffix

        if not self.original_name:
            self.original_name = None

        if not self.original_extension:
            self.original_extension = None

    def set_fake_file_attrs(self):
        self.sha256 = 'fake'
        self.size = None
        self.content_type = ''

    def set_file_attrs(self):
        sha256sum = sha256()

        for idx, chunk in enumerate(self.file.chunks()):
            if idx == 0:
                self.content_type = File.get_content_type_from_buffer(chunk)

            sha256sum.update(chunk)

        self.sha256 = sha256sum.hexdigest()
        # File size is not limited, it will be limited on upload.
        self.size = self.file.size

    @staticmethod
    def get_content_type_from_buffer(chunk: bytes):
        """Returns content type from buffer.

        Args:
            chunk (bytes): First chunk of the file.

        Note:
            First chunk - 65536 bytes is enough to determine the content type. There is no need to pass the whole file.

        Returns:
            str: The content type of the given chunk.
        """
        try:
            mime_type = MAGIC_MIME.from_buffer(chunk)
        except IsADirectoryError:
            mime_type = 'inode/directory'
        except (TypeError, SyntaxError):
            mime_type = 'application/unknown'

        return mime_type

    def get_max_size(self) -> int:
        """Returns maximum allowed uploaded file size in bytes.

        Note:
            Allowed file size depends on user, but file can be uploaded by AnonymousUser,
            in that case ``File.owner`` = None and ``accounts.models.DEFAULT_MAX_FILE_SIZE`` will be returned.

        Returns:
            int: Maximum allowed file size in bytes.
        """
        if self.owner is not None:
            return self.owner.max_file_size

        return DEFAULT_MAX_FILE_SIZE

    def allow_upload(self) -> bool:
        """Determines if the file can be uploaded to the server.

        Returns:
            bool: True if file is allowed to upload, False otherwise.
        """
        return self.get_max_size() > self.file.size
