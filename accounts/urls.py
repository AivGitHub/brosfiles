from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import Account, FileView, SigInView, SignUpView


app_name = 'accounts'


urlpatterns = [
    path('', Account.as_view(), name='index'),
    path('files/<str:url_path>/', FileView.as_view(), name='file'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('signin/', SigInView.as_view(), name='signin'),
    path('logout/', LogoutView.as_view(template_name='accounts/auth/logout.html'), name='logout'),
]
