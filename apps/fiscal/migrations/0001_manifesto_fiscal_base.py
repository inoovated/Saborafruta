# Generated manually for Manifesto Fiscal base.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('compras', '0003_entrada_recebimento_base'),
        ('core', '0009_politicareplicacaofilial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManifestoFiscalConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('cnpj', models.CharField(max_length=18)),
                ('uf', models.CharField(max_length=2)),
                ('ambiente', models.CharField(choices=[('homologacao', 'Homologacao'), ('producao', 'Producao')], default='homologacao', max_length=20)),
                ('certificado_digital', models.FileField(blank=True, null=True, upload_to='fiscal/certificados/')),
                ('certificado_nome', models.CharField(blank=True, max_length=180)),
                ('ultimo_nsu', models.CharField(blank=True, max_length=20)),
                ('data_ultima_consulta', models.DateTimeField(blank=True, null=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(help_text='Filial proprietaria do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
            ],
            options={
                'db_table': 'manifesto_fiscal_configs',
                'ordering': ['filial', 'cnpj'],
                'unique_together': {('filial', 'cnpj', 'ambiente')},
            },
        ),
        migrations.CreateModel(
            name='ManifestoFiscalDocumento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chave_acesso', models.CharField(db_index=True, max_length=44)),
                ('nsu', models.CharField(blank=True, db_index=True, max_length=20)),
                ('cnpj_emitente', models.CharField(blank=True, db_index=True, max_length=18)),
                ('razao_social_emitente', models.CharField(blank=True, max_length=180)),
                ('data_emissao', models.DateField(blank=True, null=True)),
                ('valor_total', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('status_manifestacao', models.CharField(choices=[('nao_manifestada', 'Nao manifestada'), ('ciencia', 'Ciencia da operacao'), ('confirmada', 'Confirmada'), ('desconhecida', 'Desconhecida'), ('nao_realizada', 'Operacao nao realizada')], db_index=True, default='nao_manifestada', max_length=30)),
                ('status_download_xml', models.CharField(choices=[('resumo', 'Resumo'), ('xml_disponivel', 'XML disponivel'), ('xml_baixado', 'XML baixado'), ('importada', 'Importada'), ('erro', 'Erro')], db_index=True, default='resumo', max_length=30)),
                ('xml_resumo', models.TextField(blank=True)),
                ('xml_completo', models.TextField(blank=True)),
                ('data_importacao', models.DateTimeField(blank=True, null=True)),
                ('entrada_nf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manifestos_fiscais', to='compras.entradanf')),
                ('filial', models.ForeignKey(help_text='Filial proprietaria do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
            ],
            options={
                'db_table': 'manifesto_fiscal_documentos',
                'ordering': ['-created_at'],
                'unique_together': {('filial', 'chave_acesso')},
            },
        ),
        migrations.CreateModel(
            name='ManifestoFiscalLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tipo_evento', models.CharField(max_length=40)),
                ('requisicao_resumo', models.JSONField(blank=True, default=dict)),
                ('retorno_resumo', models.JSONField(blank=True, default=dict)),
                ('codigo_status', models.CharField(blank=True, max_length=20)),
                ('mensagem', models.TextField(blank=True)),
                ('config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs', to='fiscal.manifestofiscalconfig')),
                ('documento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='fiscal.manifestofiscaldocumento')),
            ],
            options={
                'db_table': 'manifesto_fiscal_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='manifestofiscaldocumento',
            index=models.Index(fields=['filial', 'status_download_xml'], name='manifesto_doc_filial_down_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='manifestofiscaldocumento',
            index=models.Index(fields=['filial', 'status_manifestacao'], name='manifesto_doc_filial_manif_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='manifestofiscallog',
            index=models.Index(fields=['tipo_evento'], name='manifesto_log_evento_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='manifestofiscallog',
            index=models.Index(fields=['codigo_status'], name='manifesto_log_status_idx'),
                ),
            ],
        ),
    ]
