# Generated by Django 4.1.3 on 2023-03-29 18:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_alter_subscription_max_file_size'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Payment',
        ),
    ]
