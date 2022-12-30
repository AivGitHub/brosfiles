from typing import Union

from django.http import HttpResponseForbidden
from django.http.request import HttpHeaders
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from accounts.enums import TransferType
from accounts.exceptions import NotAllowed
from accounts.forms import FileUploadForm


class Account(View):
    template_name = 'accounts/account.html'
    TRANSFER_TYPE_KEY = 'X-Transfer-Type'
    SUPPORTED_TRANSFER_TYPES = ()

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

        return HttpResponseForbidden()

    def post_transfer_type_default(self, request):
        file_upload_form: FileUploadForm = FileUploadForm(
            data=request.POST,
            files=request.FILES,
            request=request
        )

        if file_upload_form.is_valid():
            file_upload_form.save()

            return redirect(reverse('accounts:index'))

        return render(
            request=request,
            template_name=self.template_name,
            context={
                'file_upload_form': file_upload_form
            }
        )

    def _get_transfer_type(self, headers: HttpHeaders):
        transfer_type: Union[str, None] = headers.get(self.TRANSFER_TYPE_KEY, None)

        if transfer_type is None:
            return TransferType.DEFAULT

        if transfer_type.upper() not in [_type.value for _type in self.SUPPORTED_TRANSFER_TYPES]:
            raise NotAllowed()

        return TransferType[transfer_type.upper()]
