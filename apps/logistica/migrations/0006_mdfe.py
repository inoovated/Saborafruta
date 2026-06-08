"""Migration: add MDFe and DocumentoMDFe tables."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('logistica', '0005_pedido_expedicao'),
        ('cadastros', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MDFe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('numero', models.PositiveIntegerField(db_index=True)),
                ('serie', models.CharField(blank=True, default='1', max_length=3)),
                ('chave_acesso', models.CharField(blank=True, db_index=True, max_length=44)),
                ('data_emissao', models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ('data_encerramento', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[('rascunho', 'Rascunho'), ('autorizado', 'Autorizado'), ('encerrado', 'Encerrado'), ('cancelado', 'Cancelado')],
                    db_index=True, default='rascunho', max_length=20,
                )),
                ('modal', models.CharField(
                    choices=[('rodoviario', 'Rodoviário'), ('aereo', 'Aéreo'), ('aquaviario', 'Aquaviário'), ('ferroviario', 'Ferroviário')],
                    default='rodoviario', max_length=20,
                )),
                ('motorista_nome', models.CharField(blank=True, max_length=120)),
                ('motorista_cpf', models.CharField(blank=True, max_length=14)),
                ('motorista_cnh', models.CharField(blank=True, max_length=20)),
                ('veiculo_placa', models.CharField(blank=True, max_length=10)),
                ('veiculo_rntrc', models.CharField(blank=True, help_text='RNTRC do veículo', max_length=20)),
                ('veiculo_descricao', models.CharField(blank=True, max_length=100)),
                ('uf_carregamento', models.CharField(blank=True, max_length=2)),
                ('municipio_carregamento', models.CharField(blank=True, max_length=100)),
                ('percurso_ufs', models.CharField(blank=True, help_text='UFs do percurso separadas por vírgula. Ex: SP,RJ,MG', max_length=200)),
                ('uf_descarregamento', models.CharField(blank=True, max_length=2)),
                ('municipio_descarregamento', models.CharField(blank=True, max_length=100)),
                ('qtd_ctes', models.PositiveIntegerField(default=0)),
                ('qtd_nfes', models.PositiveIntegerField(default=0)),
                ('peso_total_kg', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('valor_total', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('protocolo_autorizacao', models.CharField(blank=True, max_length=60)),
                ('data_autorizacao', models.DateTimeField(blank=True, null=True)),
                ('observacao', models.TextField(blank=True)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mdfes', to=settings.AUTH_USER_MODEL)),
                ('transportadora', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mdfes', to='cadastros.transportadora')),
                ('romaneio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mdfes', to='logistica.romaneiocarga')),
            ],
            options={
                'verbose_name': 'MDF-e',
                'verbose_name_plural': 'MDF-es',
                'db_table': 'logistica_mdfe',
                'ordering': ['-data_emissao', '-numero'],
                'unique_together': {('filial', 'numero')},
            },
        ),
        migrations.AddIndex(
            model_name='mdfe',
            index=models.Index(fields=['filial', 'status', '-data_emissao'], name='log_mdfe_filial_status_idx'),
        ),
        migrations.AddIndex(
            model_name='mdfe',
            index=models.Index(fields=['filial', '-numero'], name='log_mdfe_filial_numero_idx'),
        ),
        migrations.AddIndex(
            model_name='mdfe',
            index=models.Index(fields=['chave_acesso'], name='log_mdfe_chave_idx'),
        ),
        migrations.CreateModel(
            name='DocumentoMDFe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tipo_documento', models.CharField(
                    choices=[('cte', 'CT-e'), ('nfe', 'NF-e'), ('nfce', 'NFC-e'), ('outro', 'Outro')],
                    default='cte', max_length=20,
                )),
                ('chave_acesso', models.CharField(blank=True, db_index=True, max_length=44)),
                ('numero_documento', models.CharField(blank=True, max_length=60)),
                ('serie', models.CharField(blank=True, max_length=10)),
                ('emitente_nome', models.CharField(blank=True, max_length=180)),
                ('emitente_documento', models.CharField(blank=True, max_length=20)),
                ('municipio_descarga', models.CharField(blank=True, max_length=100)),
                ('uf_descarga', models.CharField(blank=True, max_length=2)),
                ('peso_kg', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('valor', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('observacao', models.TextField(blank=True)),
                ('mdfe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='logistica.mdfe')),
            ],
            options={
                'verbose_name': 'Documento do MDF-e',
                'verbose_name_plural': 'Documentos do MDF-e',
                'db_table': 'logistica_documentos_mdfe',
                'ordering': ['id'],
            },
        ),
        migrations.AddIndex(
            model_name='documentomdfe',
            index=models.Index(fields=['mdfe'], name='log_doc_mdfe_mdfe_idx'),
        ),
        migrations.AddIndex(
            model_name='documentomdfe',
            index=models.Index(fields=['tipo_documento', 'numero_documento'], name='log_doc_mdfe_tipo_num_idx'),
        ),
        migrations.AddIndex(
            model_name='documentomdfe',
            index=models.Index(fields=['chave_acesso'], name='log_doc_mdfe_chave_idx'),
        ),
    ]
