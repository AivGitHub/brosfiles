# Generated by Django 4.1.3 on 2023-03-23 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_alter_user_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='max_file_size',
            field=models.PositiveBigIntegerField(blank=True, default=209715200, null=True, verbose_name='Maximum file size'),
        ),
    ]
