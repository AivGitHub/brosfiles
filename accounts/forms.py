from typing import Union

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

from accounts.models import DEFAULT_MAX_FILE_SIZE, File, User


class FileUploadForm(forms.ModelForm):
    file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
            }
        ),
        label=_('Upload file')
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

    def clean_file(self) -> [InMemoryUploadedFile, TemporaryUploadedFile]:
        """Cleans file object and returns cleaned file.

        Note:
            File.allow_upload can't be used here as file is not initialized yet.

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
            max_file_size = self.request.user.max_file_size

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

        Returns:
            bool: True if user anonymous, otherwise False.
        """
        return self.request and self.request.user.is_anonymous

    class Meta:
        model = File
        fields = (
            'file',
        )


class SignUpForm(UserCreationForm):
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

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password1',
            'password2',
        )

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)

        if commit:
            user.save()

        return user
