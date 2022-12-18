from django.shortcuts import render
from django.views import View


class Account(View):
    template_name = 'accounts/account.html'

    def get(self, request, *args, **kwargs):
        return render(request=request, template_name=self.template_name)
