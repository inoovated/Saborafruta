import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    As tabelas parametros_sistema e parametros_documento_fiscal ja sao
    criadas por core.0010_parametros_sistema. Esta migration apenas
    registra o estado no Django sem tocar no banco.
    """

    dependencies = [
        ('core', '0011_filial_regime_tributario'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='ParametrosSistema',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('logo', models.ImageField(blank=True, null=True, upload_to='sistema/logo/',
                                                   help_text='Logomarca exibida no topo do sistema e na tela de login.')),
                        ('email_secundario', models.EmailField(blank=True, max_length=120)),
                        ('filial', models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='parametros_sistema',
                            to='core.filial',
                        )),
                    ],
                    options={
                        'verbose_name': 'Parametros do Sistema',
                        'verbose_name_plural': 'Parametros do Sistema',
                        'db_table': 'parametros_sistema',
                    },
                ),
                migrations.CreateModel(
                    name='ParametroDocumentoFiscal',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('tipo_documento', models.CharField(max_length=20, choices=[
                            ('nfe', 'NF-e'), ('nfce', 'NFC-e'), ('cte', 'CT-e'), ('cte_os', 'CT-e OS'),
                            ('mdfe', 'MDF-e'), ('nfcom', 'NFCom'), ('nfse', 'NFS-e'),
                            ('nfse_nacional', 'NFS-e Nacional'),
                        ])),
                        ('habilitado', models.BooleanField(
                            default=False,
                            help_text='Quando ativo, o documento fica disponivel para emissao.')),
                        ('serie', models.PositiveSmallIntegerField(default=1)),
                        ('proximo_numero', models.BigIntegerField(default=1)),
                        ('ambiente', models.SmallIntegerField(
                            choices=[(1, 'Producao'), (2, 'Homologacao')], default=2)),
                        ('cfop_padrao', models.CharField(blank=True, max_length=5)),
                        ('natureza_operacao', models.CharField(blank=True, max_length=100)),
                        ('parametros', models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='documentos_fiscais',
                            to='core.parametrossistema',
                        )),
                    ],
                    options={
                        'verbose_name': 'Parametro de Documento Fiscal',
                        'verbose_name_plural': 'Parametros de Documentos Fiscais',
                        'db_table': 'parametros_documento_fiscal',
                        'ordering': ['parametros', 'tipo_documento'],
                        'unique_together': {('parametros', 'tipo_documento')},
                    },
                ),
            ],
        ),
    ]