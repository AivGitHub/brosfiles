# Generated by Django 4.1.3 on 2023-03-29 18:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_delete_payment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='item_points',
        ),
        migrations.DeleteModel(
            name='ProductItemPoint',
        ),
    ]