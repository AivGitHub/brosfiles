from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.managers import UserManager


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
