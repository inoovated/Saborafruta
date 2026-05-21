from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0004_item_entrada_ncm_xml'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntradaNFParcela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('numero', models.CharField(blank=True, max_length=40)),
                ('data_vencimento', models.DateField(blank=True, db_index=True, null=True)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=14)),
                ('forma_pagamento', models.CharField(blank=True, max_length=40)),
                ('origem', models.CharField(choices=[('xml', 'XML'), ('manual', 'Manual')], default='manual', max_length=20)),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('gerada', 'Conta gerada'), ('cancelada', 'Cancelada')], db_index=True, default='pendente', max_length=20)),
                ('fornecedor_pendente', models.BooleanField(db_index=True, default=False)),
                ('emitente_documento_xml', models.CharField(blank=True, max_length=18)),
                ('emitente_nome_xml', models.CharField(blank=True, max_length=180)),
                ('conta_pagar_id', models.BigIntegerField(blank=True, null=True)),
                ('observacao', models.CharField(blank=True, max_length=255)),
                ('entrada', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parcelas_financeiras', to='compras.entradanf')),
            ],
            options={
                'verbose_name': 'Parcela da entrada',
                'verbose_name_plural': 'Parcelas da entrada',
                'db_table': 'entradas_nf_parcelas',
                'ordering': ['entrada', 'data_vencimento', 'numero'],
            },
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='entradanfparcela',
            index=models.Index(fields=['entrada', 'status'], name='entrada_parcela_status_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='entradanfparcela',
            index=models.Index(fields=['entrada', 'origem'], name='entrada_parcela_origem_idx'),
                ),
            ],
        ),
    ]
