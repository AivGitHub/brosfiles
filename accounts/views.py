from datetime import timedelta
from typing import Optional, Union

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.http.request import HttpHeaders
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from payments import PaymentStatus
from payments import get_payment_model, RedirectNeeded

from accounts.dataclasses import SignedURLReturnObject
from accounts.enums import TransferType
from accounts.exceptions import NotAllowed
from accounts.forms import ChangePasswordForm, SignInForm, FileUploadForm, SignUpForm
from accounts.models import File, Subscription

PAYMENT_MODEL = get_payment_model()


BOOK_CONTENT_TYPES = (
    'application/vnd.amazon.ebook',
    'application/epub+zip',
)


IMAGE_CONTENT_TYPES = (
    'image/avif',
    'image/bmp',
    'image/gif',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'image/webp',
)


ARCHIVE_CONTENT_TYPES = (
    'application/x-bzip',
    'application/x-bzip2',
    'application/gzip',
    'application/vnd.rar',
    'application/x-tar',
    'application/zip',
    'application/x-7z-compressed',
)


DOCUMENT_CONTENT_TYPES = (
    'application/x-abiword',
    'application/x-freearc',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.oasis.opendocument.presentation',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.text',
    'application/pdf',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/rtf',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
)


AUDIO_CONTENT_TYPES = (
    'audio/aac',
    'audio/midi',
    'audio/x-midi',
    'audio/mpeg',
    'audio/ogg',
    'audio/wav',
    'audio/webm',
    'audio/3gpp',
    'audio/3gpp2',
)


VIDEO_CONTENT_TYPES = (
    'video/mp4',
    'video/mpeg',
    'video/ogg',
    'video/mp2t',
    'video/webm',
    'video/3gpp',
    'video/3gpp2',
)


CATEGORIES = {
    'books': {
        'content_types': BOOK_CONTENT_TYPES,
        'verbose_name': _('Books'),
    },
    'images': {
        'content_types': IMAGE_CONTENT_TYPES,
        'verbose_name': _('Images'),
    },
    'archives': {
        'content_types': ARCHIVE_CONTENT_TYPES,
        'verbose_name': _('Archives'),
    },
    'documents': {
        'content_types': DOCUMENT_CONTENT_TYPES,
        'verbose_name': _('Documents'),
    },
    'audios': {
        'content_types': AUDIO_CONTENT_TYPES,
        'verbose_name': _('Audios'),
    },
    'videos': {
        'content_types': VIDEO_CONTENT_TYPES,
        'verbose_name': _('Videos'),
    },
    'default': {
        'content_types': None,
        'verbose_name': _('All files'),
    },
}


class Account(View):
    template_name = 'accounts/account.html'
    page_size = 12
    # Looks like the max length is 2 ** 8, but 2 ** 6 is big enough
    max_search_length: int = 2 ** 6
    TRANSFER_TYPE_KEY = 'X-Transfer-Type'
    SUPPORTED_TRANSFER_TYPES = (TransferType.SIGNED_URL,)

    def check_search_length(self, search_query: str):
        if self.max_search_length >= len(search_query):
            return True

        raise PermissionDenied()

    # noinspection PyMethodMayBeStatic
    def get_condition(self, user, current_category, search_query=None) -> dict:
        cond: dict = dict(
            owner=user
        )
        content_types = current_category['content_types']

        if content_types is not None:
            # In case of default - all files content_types can be None
            cond.update(dict(content_type__in=content_types))

        if search_query is not None and self.check_search_length(search_query):
            cond.update(dict(original_full_name__icontains=search_query))

        return cond

    # noinspection PyMethodMayBeStatic
    def get_current_category(self, category) -> dict:
        try:
            current_category: dict = CATEGORIES[category]
        except KeyError:
            raise PermissionDenied()

        current_category.update(dict(name=category))

        return current_category

    def get(self, request, *args, **kwargs):
        file_upload_form: FileUploadForm = FileUploadForm(request=request)

        if not request.user.is_authenticated:
            return render(
                request=request,
                template_name=self.template_name,
                context={
                    'file_upload_form': file_upload_form,
                    'files': None,
                }
            )

        category: str = request.GET.get('category', 'default')
        search_query: str = request.GET.get('q', None)

        current_category: dict = self.get_current_category(category)
        cond: dict = self.get_condition(request.user, current_category, search_query=search_query)

        paginator: Paginator = Paginator(
            File.objects.filter(**cond),
            self.page_size
        )
        files: Paginator = paginator.get_page(request.GET.get('page'))

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file_upload_form': file_upload_form,
                'files': files,
                'categories': CATEGORIES,
                'current_category': current_category,
            }
        )

    def upload(self, request):
        transfer_type = self._get_transfer_type(request.headers)

        if transfer_type == TransferType.DEFAULT:
            return self._default_upload(request)

        raise NotAllowed()

    def _default_upload(self, request):
        file_upload_form: FileUploadForm = FileUploadForm(
            data=request.POST,
            files=request.FILES,
            request=request
        )

        if file_upload_form.is_valid():
            file_upload_form.save()

            return redirect(
                reverse(
                    'accounts:file',
                    kwargs={
                        'url_path': file_upload_form.instance.url_path
                    }
                )
            )

        if not request.user.is_authenticated:
            return render(
                request=request,
                template_name=self.template_name,
                context={
                    'file_upload_form': file_upload_form
                }
            )

        category: str = request.GET.get('category', 'default')
        search_query: str = request.GET.get('q', None)

        current_category: dict = self.get_current_category(category)
        cond: dict = self.get_condition(request.user, current_category, search_query=search_query)

        paginator: Paginator = Paginator(
            File.objects.filter(**cond),
            self.page_size
        )
        files: Paginator = paginator.get_page(request.GET.get('page'))

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file_upload_form': file_upload_form,
                'files': files,
                'categories': CATEGORIES,
                'current_category': current_category,
            }
        )

    def post(self, request, *args, **kwargs):
        try:
            return self.upload(request)
        except NotAllowed:
            return HttpResponseForbidden()

    def _get_transfer_type(self, headers: HttpHeaders):
        transfer_type: Union[str, None] = headers.get(self.TRANSFER_TYPE_KEY, None)

        if transfer_type is None:
            return TransferType.DEFAULT

        if transfer_type.upper() not in [_type.value for _type in self.SUPPORTED_TRANSFER_TYPES]:
            raise NotAllowed()

        return TransferType[transfer_type.upper()]


class FileView(View):
    template_name = 'accounts/file.html'
    ONE_HOUR: int = 60 * 60

    def get(self, request, *args, **kwargs):
        url_path = kwargs.get('url_path')

        if url_path is None:
            return redirect(reverse('accounts:index'))

        try:
            file = File.objects.get(url_path=url_path)
        except File.DoesNotExist:
            return redirect(reverse('accounts:index'))

        if not file.is_user_has_access(request.user):
            raise PermissionDenied()

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file': file,
                'upload_url': None,
                'expiration': None,
            }
        )

    def post(self, request, *args, **kwargs):
        url_path = kwargs.get('url_path')

        if url_path is None:
            return redirect(reverse('accounts:index'))

        try:
            file = File.objects.get(url_path=url_path)
        except File.DoesNotExist:
            return redirect(reverse('accounts:index'))

        expiration = self.ONE_HOUR
        signed_url_object: SignedURLReturnObject = file.generate_download_signed_url(expiration=expiration)

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file': file,
                'upload_url': signed_url_object.url,
                'expiration': timedelta(seconds=expiration),
            }
        )


class SignUpView(View):
    template = 'accounts/auth/signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('accounts:index'))

        return super(SignUpView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        signup_form = SignUpForm()

        return render(
            request=request,
            template_name=self.template,
            context={
                'signup_form': signup_form
            }
        )

    def post(self, request, *args, **kwargs):
        signup_form: SignUpForm = SignUpForm(
            data=request.POST
        )

        if signup_form.is_valid():
            signup_form.save()
            messages.success(request, _('%s, you can sign in now!' % signup_form.cleaned_data.get('username')))

            return redirect(reverse('accounts:signin'))

        return render(
            request=request,
            template_name=self.template,
            context={
                'signup_form': signup_form
            }
        )


class SigInView(LoginView):
    template = 'accounts/auth/signin.html'
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        signin_form = SignInForm()

        return render(
            request=request,
            template_name=self.template,
            context={
                'signin_form': signin_form
            }
        )

    def post(self, request, *args, **kwargs):
        signin_form: SignInForm = SignInForm(
            data=request.POST
        )

        if signin_form.is_valid():
            username = signin_form.cleaned_data.get('username')
            password = signin_form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return redirect(reverse('accounts:index'))

        messages.error(request, _('Invalid username or password.'))

        return render(
            request=request,
            template_name=self.template,
            context={
                'signin_form': signin_form
            }
        )


class ProductsView(LoginRequiredMixin, View):
    template_name = 'accounts/products.html'

    def get(self, request, *args, **kwargs):
        # TODO: Don't do like this
        products = Subscription.objects.all()

        return render(
            request,
            template_name=self.template_name,
            context={
                'products': products,
            }
        )

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')

        if product_id is None:
            raise PermissionDenied()

        try:
            product = Subscription.objects.get(id=product_id)
        except Subscription.DoesNotExist:
            raise PermissionDenied()

        payment = PAYMENT_MODEL.objects.create(
            variant='default',
            total=product.price,
            currency=product.currency,
            customer_ip_address=request.META.get('REMOTE_ADDR', ''),
            billing_email=request.user.email,
            client=request.user,
            product=product
        )

        return redirect(
            reverse(
                'accounts:process_payment',
                kwargs={
                    'payment_hex': payment.payment_hex
                }
            )
        )


class ProcessPaymentView(LoginRequiredMixin, View):
    template_name = 'accounts/payment.html'
    ALLOWED_STATUSES = (
        PaymentStatus.INPUT,
        PaymentStatus.PREAUTH,
        PaymentStatus.WAITING,
    )

    def get_payment(self, payment_hex):
        try:
            payment = PAYMENT_MODEL.objects.get(payment_hex=payment_hex)
        except PAYMENT_MODEL.DoesNotExist:
            raise PermissionDenied()

        if payment.status not in self.ALLOWED_STATUSES:
            raise PermissionDenied()

        return payment

    def get(self, request, *args, **kwargs):
        payment_hex = kwargs.get('payment_hex')

        if payment_hex is None:
            raise PermissionDenied()

        payment = self.get_payment(payment_hex)

        form = payment.get_form()

        return render(
            request,
            template_name=self.template_name,
            context={
                'form': form,
                'payment': payment,
            }
        )

    def post(self, request, *args, **kwargs):
        payment_hex = kwargs.get('payment_hex')

        if payment_hex is None:
            raise PermissionDenied()

        payment = self.get_payment(payment_hex)

        try:
            form = payment.get_form(data=request.POST)
        except RedirectNeeded as redirect_link:
            return redirect('%s' % redirect_link)

        return render(
            request,
            template_name=self.template_name,
            context={
                'form': form,
                'payment': payment,
            }
        )


class PaymentCallbackView(LoginRequiredMixin, View):
    template_name = 'accounts/callbacks/payment.html'
    ALLOWED_PAYMENT_STATUSES = ('success', 'failure',)
    EXPIRATION_TIME = 60 * 30

    def is_payment_expired(self, payment):
        return payment.created + timedelta(seconds=self.EXPIRATION_TIME) < timezone.now()

    def get(self, request, *args, **kwargs):
        payment_status = kwargs.get('payment_status')
        payment_hex = request.GET.get('ph')

        if payment_hex is None or payment_status not in self.ALLOWED_PAYMENT_STATUSES:
            raise PermissionDenied()

        try:
            payment = PAYMENT_MODEL.objects.get(payment_hex=payment_hex)
        except PAYMENT_MODEL.DoesNotExist:
            raise PermissionDenied()

        if self.is_payment_expired(payment):
            raise PermissionDenied()

        payment.configure_user()

        return render(
            request,
            template_name=self.template_name,
            context={
                'payment': payment,
                'is_success': payment_status == 'success',
            }
        )


class SettingsView(LoginRequiredMixin, View):
    template_name = 'accounts/settings.html'

    def get(self, request, *args, **kwargs):
        change_password_form = ChangePasswordForm(user=request.user)

        return render(
            request,
            template_name=self.template_name,
            context={
                'change_password_form': change_password_form,
            }
        )

    def post(self, request, *args, **kwargs):
        change_password_form = ChangePasswordForm(data=request.POST, user=request.user)

        if change_password_form.is_valid():
            messages.success(request, _('Password has been changed'))

            change_password_form.save()
            login(request, request.user)

            return redirect(reverse('accounts:settings'))

        return render(
            request,
            template_name=self.template_name,
            context={
                'change_password_form': change_password_form,
            }
        )
