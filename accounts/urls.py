from django.urls import path

from accounts.views import Account, FileView


app_name = 'accounts'


urlpatterns = [
    path('', Account.as_view(), name='index'),
    path('files/<str:url_path>/', FileView.as_view(), name='file'),
]
