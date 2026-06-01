# Generated manually for Entrada de Mercadoria / Manifesto base.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0002_compat_legacy_required_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entradanf',
            name='status',
            field=models.CharField(
                choices=[
                    ('rascunho', 'Rascunho'),
                    ('aguardando_vinculos', 'Aguardando vinculos'),
                    ('aguardando_conferencia', 'Aguardando conferencia'),
                    ('com_diferencas', 'Com diferencas'),
                    ('conferida', 'Conferida'),
                    ('processando', 'Processando'),
                    ('efetivada', 'Efetivada'),
                    ('cancelada', 'Cancelada'),
                    ('estornada', 'Estornada'),
                ],
                db_index=True,
                default='rascunho',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='origem_entrada',
            field=models.CharField(
                choices=[
                    ('manual', 'Manual'),
                    ('xml', 'XML'),
                    ('chave', 'Chave de acesso'),
                    ('manifesto', 'Manifesto fiscal'),
                ],
                db_index=True,
                default='manual',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='xml_original',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='xml_nome_arquivo',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='destinatario_documento_xml',
            field=models.CharField(blank=True, max_length=18),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='destinatario_nome_xml',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='destinatario_documento_diferente',
            field=models.BooleanField(
                default=False,
                help_text='Apenas alerta operacional; nao bloqueia a entrada.',
            ),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='fornecedor_pendente',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_cnpj_xml',
            field=models.CharField(blank=True, db_index=True, max_length=18),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_razao_social_xml',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_nome_fantasia_xml',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_ie_xml',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_endereco_xml',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_municipio_xml',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_uf_xml',
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_cep_xml',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='entradanf',
            name='emitente_telefone_xml',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name='itementradanf',
            name='produto',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='+',
                to='produtos.produto',
            ),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='quantidade_xml',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='quantidade_estoque',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='quantidade_recebida',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='unidade_xml',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='unidade_estoque',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='fator_conversao',
            field=models.DecimalField(decimal_places=4, default=1, max_digits=12),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='ean_xml',
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='codigo_produto_fornecedor',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='descricao_xml',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='diferenca_tipo',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='diferenca_descricao',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='diferenca_bloqueante',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='itementradanf',
            name='justificativa_diferenca',
            field=models.TextField(blank=True),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='entradanf',
            index=models.Index(fields=['filial', 'origem_entrada'], name='entradas_nf_filial_origem_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='entradanf',
            index=models.Index(fields=['filial', 'fornecedor_pendente'], name='entradas_nf_fornpend_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='itementradanf',
            index=models.Index(fields=['ean_xml'], name='itens_entrada_ean_xml_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='itementradanf',
            index=models.Index(fields=['entrada', 'diferenca_bloqueante'], name='itens_entrada_diff_block_idx'),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name='entradanf',
            constraint=models.UniqueConstraint(
                condition=~models.Q(chave_acesso_nf=''),
                fields=('filial', 'chave_acesso_nf'),
                name='uniq_entrada_nf_chave_por_filial',
            ),
        ),
    ]
