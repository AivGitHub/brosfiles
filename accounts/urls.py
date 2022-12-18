from django.urls import path

from accounts.views import Account


app_name = 'accounts'


urlpatterns = [
    path('', Account.as_view(), name='index'),
]
