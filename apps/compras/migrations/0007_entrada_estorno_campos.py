from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('compras', '0006_entrada_nf_custo_composicao'),
    ]

    operations = [
        migrations.AddField(
            model_name='entradanf',
            name='data_estorno',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='usuario_estorno',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entradas_estornadas', to=settings.AUTH_USER_MODEL),
        ),
    ]
