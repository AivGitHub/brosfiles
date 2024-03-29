from typing import Union

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

from accounts.models import DEFAULT_MAX_FILE_SIZE, DEFAULT_STORAGE_SIZE, File, User, UserDoesNotHaveSubscription
from docs.models import TermsOfService


class FileUploadForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
            }
        ),
        label=_('Upload file')
    )
    is_private = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input',
            }
        ),
        label=_('Private'),
        required=False,
        initial=True
    )
    max_file_size = forms.CharField(
        widget=forms.HiddenInput(),
        initial=DEFAULT_MAX_FILE_SIZE
    )
    storage_size = forms.CharField(
        widget=forms.HiddenInput(),
        initial=DEFAULT_STORAGE_SIZE
    )

    def __init__(self, *args, **kwargs) -> None:
        """Initializes the FileUploadForm.

        Example:
            >>> from io import StringIO
            >>> from django.core.handlers.wsgi import WSGIRequest
            >>> from accounts.forms import FileUploadForm
            >>> request = WSGIRequest({'REQUEST_METHOD': 'POST', 'user': None, 'wsgi.input': StringIO()})
            >>> file_form = FileUploadForm(request=request)
            >>> file_form.is_valid()
            >>> False

        Note:
            Usually request can't be accessed in Django forms.
            This form should be initialized with request.

        Returns:
            None
        """
        self.request = kwargs.pop('request', None)

        super().__init__(*args, **kwargs)

        if self.is_user_anonymous():
            self.fields.pop('is_private', None)

        if self.is_user_anonymous():
            return

        try:
            metadata = self.request.user.get_subscription_metadata()
        except UserDoesNotHaveSubscription:
            # User Does not have active subscriptions.
            return

        self.fields['max_file_size'].initial = metadata['max_file_size']
        self.fields['storage_size'].initial = metadata['storage_size']

    def clean_file(self) -> [InMemoryUploadedFile, TemporaryUploadedFile]:
        """Cleans file object and returns cleaned file.

        Returns:
            django.core.files.uploadedfile.InMemoryUploadedFile: if the file size
                less than ``django.conf.settings.DATA_UPLOAD_MAX_MEMORY_SIZE``.
            django.core.files.uploadedfile.TemporaryUploadedFile: if the file size
                more than ``django.conf.settings.DATA_UPLOAD_MAX_MEMORY_SIZE``.

        Raises:
            ValidationError: If uploaded file size more than allowed file size.
        """
        file: [InMemoryUploadedFile, TemporaryUploadedFile] = self.cleaned_data['file']
        max_file_size: int = DEFAULT_MAX_FILE_SIZE

        if not self.is_user_anonymous():
            max_file_size = self.request.user.get_max_file_size()

        if file.size > max_file_size:
            h_max_file_size: str = filesizeformat(max_file_size)

            raise ValidationError(_('File is too big. Available size is %s.' % h_max_file_size))

        return file

    def save(self, commit: bool = True) -> File:
        user: Union[User, None] = None
        ip: str = ''
        file: File = super().save(commit=False)

        if self.request is not None:
            ip = self.request.META.get('REMOTE_ADDR', '')

        if not self.is_user_anonymous():
            user = self.request.user

        file.owner = user
        file.ip = ip

        if commit:
            file.save()

        return file

    def is_user_anonymous(self) -> bool:
        """Determines if the user is anonymous.

        Usually forms know nothing about request, so if request is ``None``
        we assume that user is anonymous.

        Returns:
            bool: True if user anonymous, otherwise False.
        """
        if self.request is None:
            return True

        return self.request.user.is_anonymous

    class Meta:
        model = File
        fields = (
            'file',
            'is_private',
        )


class SignUpForm(UserCreationForm):
    USERNAME_MIN_LENGTH = 5

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
            }
        ),
        required=True
    )
    first_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    last_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
            }
        ),
        label=_('Password')
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
            }
        ),
        label=_('Confirm password')
    )
    terms_of_service = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input',
            }
        ),
        required=True,
        initial=False
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password1',
            'password2',
            'terms_of_service',
        )

    def clean_terms_of_service(self) -> TermsOfService:
        terms_of_service: str = self.cleaned_data['terms_of_service']

        if terms_of_service is False:
            raise ValidationError('You need to agree on Terms Of Service')

        return TermsOfService.objects.latest()

    def clean_username(self) -> str:
        username: str = self.cleaned_data['username']

        if len(username) < self.USERNAME_MIN_LENGTH:
            raise ValidationError("Username can't be less then %s symbols" % self.USERNAME_MIN_LENGTH)

        return username

    def clean(self) -> dict:
        cleaned_data: dict = super().clean()
        first_name: str = cleaned_data['first_name']
        last_name: str = cleaned_data['last_name']

        if first_name == last_name:
            raise ValidationError(
                {
                    "first_name": _("I've noticed a weired activity, "
                                    "that users sign up with the same first name as a last name. "
                                    "Now it's restricted in case these are bots.")
                }
            ) from None

        return cleaned_data

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)

        user.is_active = False
        if commit:
            user.save()

        return user


class SignInForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'autofocus': True,
                'class': 'form-control',
                'placeholder': _('Username'),
            }
        )
    )
    password = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'class': 'form-control',
                'placeholder': _('Password'),
            }
        ),
    )


class ChangePasswordForm(PasswordChangeForm):
    old_password = forms.CharField(
        label=_('Old password'),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'autofocus': True,
                'class': 'form-control',

            }
        ),
    )
    new_password1 = forms.CharField(
        label=_('New password'),
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'new-password',
                'class': 'form-control',
            }
        ),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_('Confirm new password'),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'new-password',
                'class': 'form-control',
            }
        ),
    )
