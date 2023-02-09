from http import HTTPStatus

from django.shortcuts import render


def page_not_found(request, exception):
    return render(request, 'base/errors/error_404.html', status=HTTPStatus.NOT_FOUND)


def csrf_failure(request, reason=''):
    return render(request, 'base/errors/csrf_403.html', status=HTTPStatus.FORBIDDEN)


def page_forbidden(request, exception):
    return render(request, 'base/errors/error_403.html', status=HTTPStatus.FORBIDDEN)
