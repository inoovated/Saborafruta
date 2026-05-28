"""Migration: create financeiro_credito_cliente table."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0006_rename_clientes_fi_filial_a9398f_idx_clientes_fi_filial__cb2c0a_idx_and_more'),
        ('core', '0001_initial'),
        ('financeiro', '0004_merge_20260522_1038'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditoCliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('valor', models.DecimalField(decimal_places=2, help_text='Valor total do crédito gerado.', max_digits=14)),
                ('valor_utilizado', models.DecimalField(decimal_places=2, default=0, help_text='Valor já utilizado do crédito.', max_digits=14)),
                ('motivo', models.CharField(help_text="Ex.: 'devolucao', 'ajuste'.", max_length=100)),
                ('documento_numero', models.CharField(blank=True, max_length=30)),
                ('cfop', models.CharField(blank=True, max_length=10)),
                ('observacao', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('disponivel', 'Disponível'), ('utilizado', 'Utilizado'), ('cancelado', 'Cancelado')],
                    db_index=True,
                    default='disponivel',
                    max_length=20,
                )),
                ('cliente', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='creditos',
                    to='cadastros.cliente',
                )),
                ('filial', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='creditos_clientes',
                    to='core.filial',
                )),
                ('usuario', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='creditos_clientes_gerados',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Crédito de Cliente',
                'verbose_name_plural': 'Créditos de Clientes',
                'db_table': 'financeiro_credito_cliente',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['filial', 'cliente', 'status'], name='fin_credcli_filial_idx'),
                ],
            },
        ),
    ]
