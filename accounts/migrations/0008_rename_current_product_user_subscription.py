# Generated by Django 4.1.3 on 2023-02-28 18:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_rename_product_subscription'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='current_product',
            new_name='subscription',
        ),
    ]
