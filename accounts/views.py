from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from accounts.forms import FileUploadForm


class Account(View):
    template_name = 'accounts/account.html'

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
