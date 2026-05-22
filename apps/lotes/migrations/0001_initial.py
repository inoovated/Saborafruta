import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('estoque', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InspecaoLote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('data_inspecao', models.DateTimeField()),
                ('resultado', models.CharField(
                    choices=[
                        ('aprovado', 'Aprovado'),
                        ('reprovado', 'Reprovado'),
                        ('quarentena', 'Em Quarentena'),
                        ('pendente', 'Pendente'),
                    ],
                    db_index=True,
                    default='pendente',
                    max_length=20,
                )),
                ('parecer', models.TextField(blank=True, help_text='Descrição técnica do resultado')),
                ('observacao', models.TextField(blank=True)),
                ('lote', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='inspecoes',
                    to='estoque.loteproduto',
                )),
                ('responsavel', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='inspecoes_lote',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Inspeção de Lote',
                'verbose_name_plural': 'Inspeções de Lote',
                'db_table': 'lotes_inspecoes',
                'ordering': ['-data_inspecao'],
            },
        ),
    ]
