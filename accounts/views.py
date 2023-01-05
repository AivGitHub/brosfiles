from datetime import timedelta
from typing import Union

from django.http import HttpResponseForbidden, JsonResponse
from django.http.request import HttpHeaders
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.datastructures import MultiValueDictKeyError
from django.views import View

from accounts.dataclasses import SignedURLReturnObject
from accounts.enums import TransferType, UploadAction, UploadStatus
from accounts.exceptions import NotAllowed
from accounts.forms import FileUploadForm
from accounts.models import File, generate_fake_file
from base.exceptions import FatalSignatureError, SignatureExpiredError
from base.utils import decode_jwt_signature, generate_jwt_signature


class Account(View):
    template_name = 'accounts/account.html'
    TRANSFER_TYPE_KEY = 'X-Transfer-Type'
    SUPPORTED_TRANSFER_TYPES = (TransferType.SIGNED_URL,)
    SIGNED_URL_REQUEST_KEY = 'X-Signed-URL-request'
    UPLOAD_ACTION_KEY = 'X-Upload-Action'
    UPLOAD_SIGNATURE_KEY = 'X-Upload-Signature'

    def get(self, request, *args, **kwargs):
        file_upload_form: FileUploadForm = FileUploadForm()

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file_upload_form': file_upload_form
            }
        )

    def post(self, request, *args, **kwargs):
        try:
            transfer_type = self._get_transfer_type(request.headers)
        except NotAllowed:
            return HttpResponseForbidden()

        if transfer_type == TransferType.DEFAULT:
            return self.post_transfer_type_default(request)
        elif transfer_type == TransferType.SIGNED_URL:
            try:
                return self.post_transfer_type_signed_url(request)
            except NotAllowed:
                return HttpResponseForbidden()

        return HttpResponseForbidden()

    def post_transfer_type_default(self, request):
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

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file_upload_form': file_upload_form
            }
        )

    def post_transfer_type_signed_url(self, request):
        upload_action: str = self.get_header(request.headers, self.UPLOAD_ACTION_KEY)

        if upload_action.upper() == UploadAction.START.value:
            request_key: str = self.get_header(request.headers, self.SIGNED_URL_REQUEST_KEY)
            site_url: str = '%s://%s' % (request.scheme, request.META['HTTP_HOST'])

            return JsonResponse(self.start_upload_signed_url(request.POST, request_key, site_url))
        elif upload_action.upper() == UploadAction.FINISH.value:
            signature: str = self.get_header(request.headers, self.UPLOAD_SIGNATURE_KEY)

            return JsonResponse(self.finish_upload_signed_url(signature))
        else:
            raise NotAllowed()

    def _get_transfer_type(self, headers: HttpHeaders):
        transfer_type: Union[str, None] = headers.get(self.TRANSFER_TYPE_KEY, None)

        if transfer_type is None:
            return TransferType.DEFAULT

        if transfer_type.upper() not in [_type.value for _type in self.SUPPORTED_TRANSFER_TYPES]:
            raise NotAllowed()

        return TransferType[transfer_type.upper()]

    # noinspection PyMethodMayBeStatic
    def finish_upload_signed_url(self, signature):
        try:
            payload = decode_jwt_signature(signature)
        except (FatalSignatureError, SignatureExpiredError):
            raise NotAllowed()

        try:
            upload_hash = payload['upload_hash']
        except KeyError:
            raise NotAllowed()

        file = File.objects.get(upload_hex=upload_hash)

        try:
            file.save()
        except FileNotFoundError:
            raise NotAllowed()

        return {
            'redirect_url': reverse('accounts:file', kwargs={'url_path': file.url_path})
        }

    # noinspection PyMethodMayBeStatic
    def start_upload_signed_url(self, body: dict, request_key: str, site_url: str):
        payload: dict = dict()

        try:
            filename: str = body['filename']
        except MultiValueDictKeyError:
            raise NotAllowed()

        file: File = generate_fake_file(filename)

        for key, value in body.items():
            payload[key] = value

        payload.update(
            {
                'request_key': request_key,
                'upload_hash': file.upload_hex,
                'filename': filename,
            }
        )

        token = generate_jwt_signature(payload)
        upload_signed_return_object = file.generate_upload_signed_url(
            headers={
                'Access-Control-Allow-Origin': site_url,
            }
        )

        return {
            'status': UploadStatus.PENDING.value,
            'token': token,
            'request_data': {
                'url': upload_signed_return_object.url,
                'headers': upload_signed_return_object.headers,
                'method': upload_signed_return_object.method,
            }
        }

    # noinspection PyMethodMayBeStatic
    def get_header(self, headers, header_key, raised_exception=NotAllowed):
        header_value = headers.get(header_key, None)

        if header_value is None and raised_exception is not None:
            raise raised_exception()

        return header_value


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
