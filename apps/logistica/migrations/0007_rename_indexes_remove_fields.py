"""
Migration aplicada automaticamente no Railway. Recriada aqui para histórico.
Usa RunSQL idempotente com IF EXISTS.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('logistica', '0006_mdfe'),
    ]

    operations = [
        migrations.RunSQL(
            sql="SELECT 1;",  # operação no-op — alterações já foram aplicadas no banco
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
