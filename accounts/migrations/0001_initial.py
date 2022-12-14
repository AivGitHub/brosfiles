# Generated by Django 4.1.3 on 2022-12-14 22:04

import accounts.managers
import accounts.models
import accounts.utils
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='150 characters or fewer. Letters and digits only.', max_length=64, unique=True, verbose_name='username')),
                ('first_name', models.CharField(max_length=150, verbose_name='First name')),
                ('last_name', models.CharField(max_length=50, verbose_name='Last name')),
                ('email', models.EmailField(blank=True, default=None, error_messages={'unique': 'A user with that email already exists.'}, max_length=254, null=True, verbose_name='Email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='Staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='Active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date joined')),
                ('public_key', models.TextField(blank=True, max_length=2056, null=True, verbose_name='Public key')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
            managers=[
                ('objects', accounts.managers.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(blank=True, max_length=512, null=True, upload_to=accounts.utils.file_upload_path, verbose_name='File')),
                ('sha256', models.CharField(editable=False, max_length=64, verbose_name='File sha256 hash')),
                ('original_full_name', models.CharField(editable=False, max_length=256, verbose_name='Original full name')),
                ('original_name', models.CharField(blank=True, editable=False, max_length=128, null=True, verbose_name='Original name')),
                ('original_extension', models.CharField(blank=True, editable=False, max_length=64, null=True, verbose_name='Original extension')),
                ('content_type', models.CharField(editable=False, max_length=64, verbose_name='Content type')),
                ('is_private', models.BooleanField(default=False, verbose_name='Is private')),
                ('is_encrypted', models.BooleanField(default=False, editable=False, verbose_name='Is encrypted')),
                ('size', models.IntegerField(blank=True, editable=False, null=True, verbose_name='Size')),
                ('exif', models.TextField(blank=True, editable=False, max_length=65535, null=True, verbose_name='Exif data')),
                ('ip', models.CharField(editable=False, max_length=16, verbose_name='IP')),
                ('upload_hex', models.CharField(default=accounts.models.get_upload_hex, editable=False, max_length=32, unique=True, verbose_name='Upload hex')),
                ('url_path', models.CharField(default=accounts.models.get_url_path, editable=False, max_length=64, unique=True, verbose_name='URL Path')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
