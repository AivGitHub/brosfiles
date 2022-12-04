from http import HTTPStatus

from django.http import HttpResponse
from django.views import View


class Health(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(status=HTTPStatus.OK)
