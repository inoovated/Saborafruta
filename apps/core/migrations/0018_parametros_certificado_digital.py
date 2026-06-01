from django.db import migrations


class Migration(migrations.Migration):
    """No-op: os campos do certificado já são criados em core.0011."""

    dependencies = [
        ('core', '0017_rename_registros_a_modulo'),
    ]

    operations = []
