from django.db import migrations

from base.utils import create_superuser


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.RunPython(create_superuser)]
