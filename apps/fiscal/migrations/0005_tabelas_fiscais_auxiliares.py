from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fiscal', '0004_alter_manifestofiscalconfig_filial_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegraFiscalUF',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uf', models.CharField(choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapa'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceara'), ('DF', 'Distrito Federal'), ('ES', 'Espirito Santo'), ('GO', 'Goias'), ('MA', 'Maranhao'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Para'), ('PB', 'Paraiba'), ('PR', 'Parana'), ('PE', 'Pernambuco'), ('PI', 'Piaui'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondonia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'Sao Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], db_index=True, max_length=2)),
                ('ncm', models.CharField(blank=True, db_index=True, max_length=8)),
                ('cest', models.CharField(blank=True, db_index=True, max_length=7)),
                ('cfop', models.CharField(blank=True, db_index=True, max_length=5)),
                ('regime_tributario', models.CharField(blank=True, db_index=True, max_length=30)),
                ('aliquota_icms', models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True)),
                ('aliquota_fcp', models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True)),
                ('mva', models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True)),
                ('reducao_base', models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True)),
                ('fonte', models.CharField(blank=True, max_length=120)),
                ('versao', models.CharField(blank=True, max_length=40)),
                ('vigencia_inicio', models.DateField(blank=True, null=True)),
                ('vigencia_fim', models.DateField(blank=True, null=True)),
                ('observacao', models.TextField(blank=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'Regra Fiscal por UF',
                'verbose_name_plural': 'Regras Fiscais por UF',
                'db_table': 'regras_fiscais_uf',
                'ordering': ['uf', 'ncm', 'cfop'],
            },
        ),
        migrations.CreateModel(
            name='TabelaFiscalAuxiliar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tipo', models.CharField(choices=[('ncm', 'NCM'), ('cest', 'CEST'), ('cfop', 'CFOP'), ('ipi_tipi', 'IPI/TIPI'), ('cst_pis_cofins', 'CST PIS/COFINS')], db_index=True, max_length=20)),
                ('codigo', models.CharField(db_index=True, max_length=20)),
                ('descricao', models.CharField(max_length=255)),
                ('ncm', models.CharField(blank=True, db_index=True, max_length=8)),
                ('cest', models.CharField(blank=True, db_index=True, max_length=7)),
                ('uf', models.CharField(blank=True, choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapa'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceara'), ('DF', 'Distrito Federal'), ('ES', 'Espirito Santo'), ('GO', 'Goias'), ('MA', 'Maranhao'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Para'), ('PB', 'Paraiba'), ('PR', 'Parana'), ('PE', 'Pernambuco'), ('PI', 'Piaui'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondonia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'Sao Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], db_index=True, max_length=2)),
                ('aliquota', models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True)),
                ('fonte', models.CharField(blank=True, max_length=120)),
                ('versao', models.CharField(blank=True, max_length=40)),
                ('vigencia_inicio', models.DateField(blank=True, null=True)),
                ('vigencia_fim', models.DateField(blank=True, null=True)),
                ('observacao', models.TextField(blank=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'Tabela Fiscal Auxiliar',
                'verbose_name_plural': 'Tabelas Fiscais Auxiliares',
                'db_table': 'tabelas_fiscais_auxiliares',
                'ordering': ['tipo', 'codigo', 'uf'],
            },
        ),
        migrations.AddIndex(
            model_name='regrafiscaluf',
            index=models.Index(fields=['uf', 'ncm', 'ativo'], name='regras_fisc_uf_aa0e88_idx'),
        ),
        migrations.AddIndex(
            model_name='regrafiscaluf',
            index=models.Index(fields=['uf', 'cest', 'ativo'], name='regras_fisc_uf_239c91_idx'),
        ),
        migrations.AddIndex(
            model_name='regrafiscaluf',
            index=models.Index(fields=['uf', 'cfop', 'ativo'], name='regras_fisc_uf_643c37_idx'),
        ),
        migrations.AddIndex(
            model_name='tabelafiscalauxiliar',
            index=models.Index(fields=['tipo', 'codigo', 'ativo'], name='tabelas_fis_tipo_3d9938_idx'),
        ),
        migrations.AddIndex(
            model_name='tabelafiscalauxiliar',
            index=models.Index(fields=['tipo', 'ncm', 'ativo'], name='tabelas_fis_tipo_fa2505_idx'),
        ),
        migrations.AddIndex(
            model_name='tabelafiscalauxiliar',
            index=models.Index(fields=['tipo', 'uf', 'ativo'], name='tabelas_fis_tipo_55bf9c_idx'),
        ),
    ]
