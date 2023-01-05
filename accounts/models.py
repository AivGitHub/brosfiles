import datetime
from hashlib import sha256
from pathlib import Path
import secrets
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.files.storage import default_storage as storage
from django.core.mail import send_mail
from django.db import models
from django.db.models.fields.files import FieldFile
from django.template.defaultfilters import filesizeformat
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from google.cloud.storage.blob import Blob
import magic

from accounts.dataclasses import SignedURLReturnObject
from accounts.enums import SignedURLMethod
from accounts.exceptions import NotSupportedSignURLMethod
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

    DEFAULT_SIGNED_URL_EXPIRATION = 15 * 60
    MIN_SIGNED_URL_EXPIRATION = 0
    MAX_SIGNED_URL_EXPIRATION = 7 * 24 * 60 * 60
    SUPPORTED_METHODS = (
        SignedURLMethod.PUT,
        SignedURLMethod.GET,
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

    def get_signed_url_expiration(self, expiration: Optional[int]) -> int:
        """Returns expiration time of the signed URL.

        Args:
            expiration (int, optional): Expiration time in seconds or None.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.

        Returns:
            int: Expiration time of the signed URL in seconds.

        Raises:
            ValueError: If wrong expiration time is specified.
        """
        if expiration is None:
            return self.DEFAULT_SIGNED_URL_EXPIRATION

        if self.MIN_SIGNED_URL_EXPIRATION > expiration > self.MAX_SIGNED_URL_EXPIRATION:
            raise ValueError(
                'Wrong expiration time; min=%s, max=%s' % (
                    self.MIN_SIGNED_URL_EXPIRATION,
                    self.MAX_SIGNED_URL_EXPIRATION
                )
            )

        return expiration

    def generate_upload_signed_url(
            self,
            expiration: Optional[int] = None,
            headers: Optional[dict] = None
    ) -> SignedURLReturnObject:
        """Generates upload signed URL depending on storage.

        Note:
            If ``expiration`` is not specified expiration time will be ``File.DEFAULT_SIGNED_URL_EXPIRATION``.

        Args:
            expiration (int, optional): Expiration time in seconds or None.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.
            headers (dict, optional): Extra headers.

        Returns:
            accounts.dataclasses.SignedURLReturnObject: Values that allows clients to make upload request.

        Raises:
            NotImplementedError: If storage is not supported.
        """
        expiration: int = self.get_signed_url_expiration(expiration)

        if settings.GOOGLE_CLOUD_PROJECT:
            return self.generate_google_upload_signed_url(expiration=expiration, headers=headers)

        raise NotImplementedError()

    def generate_download_signed_url(
            self,
            expiration: Optional[int] = None,
            headers: Optional[dict] = None
    ) -> SignedURLReturnObject:
        """Generates download signed URL depending on storage.

        Note:
            If ``expiration`` is not specified expiration time will be ``File.DEFAULT_SIGNED_URL_EXPIRATION``.

        Args:
            expiration (int, optional): Expiration time in seconds or None.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.
            headers (dict, optional): Extra headers.

        Returns:
            accounts.dataclasses.SignedURLReturnObject: Values that allows clients to make upload request.

        Raises:
            NotImplementedError: If storage is not supported.
        """
        expiration: int = self.get_signed_url_expiration(expiration)

        if settings.GOOGLE_CLOUD_PROJECT:
            return self.generate_google_download_signed_url(expiration=expiration, headers=headers)

        raise NotImplementedError()

    def _generate_google_signed_url(
            self,
            method: SignedURLMethod,
            expiration: Optional[int] = None,
            headers: Optional[dict] = None,
            content_type: Optional[str] = None,
            query_parameters: Optional[dict] = None
    ) -> SignedURLReturnObject:
        """Generates Google signed URL.

        Note:
            Version v4 of Google API updates headers.
                https://github.com/googleapis/python-storage/blob/main/google/cloud/storage/_signing.py#L418

        Args:
            method (accounts.enums.SignedURLMethod): Should be in ``File.SUPPORTED_METHODS``.
            expiration (int, optional): Expiration time in seconds.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.
            headers (dict, optional): Additional headers.
                For example, specifying `X-Goog-Content-Length-Range: min_size, max_size` header implies
                that the uploaded file size must be greater than `min_size` and less than `max_size`.
            content_type (str, optional): Content type of the uploaded file.
            query_parameters (dict, optional): Extra query parameters.
                Query parameters are not signed and should be used with caution.

        Returns:
            accounts.dataclasses.SignedURLReturnObject: Values that allows clients to make upload request.

        Raises:
            accounts.exceptions.NotSupportedSignURLMethod: If specified method is not supported.
        """
        if method not in self.SUPPORTED_METHODS:
            raise NotSupportedSignURLMethod()

        blob: Blob = storage.bucket.blob(self.file.name)

        expiration: int = self.get_signed_url_expiration(expiration)
        signed_url_kwargs: dict = dict(
            version='v4',
            method=method.value
        )

        if expiration is not None:
            signed_url_kwargs.update(
                dict(
                    expiration=datetime.timedelta(seconds=expiration)
                )
            )

        if content_type is not None:
            signed_url_kwargs.update(
                dict(
                    content_type=content_type
                )
            )

        if headers is not None:
            signed_url_kwargs.update(
                dict(
                    headers=headers
                )
            )

        if query_parameters is not None:
            signed_url_kwargs.update(
                dict(
                    query_parameters=query_parameters
                )
            )

        url = blob.generate_signed_url(**signed_url_kwargs)

        return SignedURLReturnObject(
            url=url,
            headers=headers,
            method=method.value
        )

    def generate_google_upload_signed_url(
            self,
            expiration: Optional[int] = None,
            headers: Optional[dict] = None
    ) -> SignedURLReturnObject:
        """Generates Google upload signed URL.

        Args:
            expiration (int, optional): Expiration time in seconds.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.
            headers (dict, optional): Extra headers.

        Returns:
            accounts.dataclasses.SignedURLReturnObject: Values that allows clients to make upload request.
        """
        max_size: int = self.get_max_size()
        expiration: int = self.get_signed_url_expiration(expiration)

        base_headers: dict = {
            'X-Goog-Content-Length-Range': '0,%s' % max_size,
        }

        if headers is not None:
            allow_origin = headers.get('Access-Control-Allow-Origin')

            if allow_origin in settings.ALLOWED_HOSTS:
                base_headers.update(headers)

        return self._generate_google_signed_url(
            SignedURLMethod.PUT,
            expiration=expiration,
            headers=base_headers,
            content_type='application/octet-stream'
        )

    def generate_google_download_signed_url(
        self,
        expiration: Optional[int] = None,
        headers: Optional[dict] = None,
        query_parameters: Optional[dict] = None
    ) -> SignedURLReturnObject:
        """Generates Google download signed URL.

        Args:
            expiration (int, optional): Expiration time in seconds.
                If specified must be greater than 0 and less than 60*60*24*7 (7 days).
                If not specified, then ``File.DEFAULT_SIGNED_URL_EXPIRATION`` will be used.
            headers (dict, optional): Extra headers.
            query_parameters (dict, optional): Additional query parameters.
                Query parameters are not signed and should be used with caution.

        Returns:
            accounts.dataclasses.SignedURLReturnObject: Values that allows clients to make upload request.
        """
        expiration: int = self.get_signed_url_expiration(expiration)

        if headers is None:
            headers = {}

        base_query_parameters: dict = {
            'response-content-disposition': 'attachment;filename="%s"' % self.original_full_name,
        }

        if query_parameters is not None:
            base_query_parameters.update(query_parameters)

        return self._generate_google_signed_url(
            SignedURLMethod.GET,
            expiration=expiration,
            headers=headers,
            query_parameters=base_query_parameters
        )

    def get_h_size(self):
        """Returns humanreadable size of the file.

        Returns:
            str: Human readable size.
        """
        return filesizeformat(self.size)


def generate_fake_file(original_name):
    file = File()

    file_field = models.FileField(upload_to=file_upload_path(File, original_name), name=original_name)
    field_file = FieldFile(field=file_field, name=file_field.upload_to, instance=models.FileField)

    file.file = field_file
    file.save(fake=True, original_full_name=original_name)

    return file
