# Generated manually for Entrada de Mercadoria equivalences.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0005_transportadora_representante_filiais'),
        ('produtos', '0020_repara_id_externo_promocoes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProdutoCodigoBarras',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ean', models.CharField(db_index=True, max_length=32)),
                ('tipo', models.CharField(choices=[('unidade', 'Unidade'), ('caixa', 'Caixa'), ('pacote', 'Pacote'), ('fornecedor', 'Fornecedor'), ('alternativo', 'Alternativo')], default='alternativo', max_length=20)),
                ('quantidade_conversao', models.DecimalField(decimal_places=4, default=1, max_digits=12)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('observacao', models.CharField(blank=True, max_length=255)),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codigos_barras', to='produtos.produto')),
            ],
            options={
                'verbose_name': 'Codigo de barras do produto',
                'verbose_name_plural': 'Codigos de barras dos produtos',
                'db_table': 'produtos_codigos_barras',
                'ordering': ['produto', 'ean'],
            },
        ),
        migrations.CreateModel(
            name='ProdutoFornecedorEquivalencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fornecedor_cnpj_xml', models.CharField(blank=True, db_index=True, max_length=18)),
                ('fornecedor_razao_social_xml', models.CharField(blank=True, max_length=180)),
                ('codigo_fornecedor', models.CharField(blank=True, db_index=True, max_length=80)),
                ('descricao_fornecedor', models.CharField(blank=True, max_length=255)),
                ('ean_utilizado', models.CharField(blank=True, db_index=True, max_length=32)),
                ('unidade_compra', models.CharField(blank=True, max_length=10)),
                ('unidade_estoque', models.CharField(blank=True, max_length=10)),
                ('fator_conversao', models.DecimalField(decimal_places=4, default=1, max_digits=12)),
                ('ultimo_custo', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('data_ultima_compra', models.DateField(blank=True, null=True)),
                ('origem', models.CharField(choices=[('xml', 'XML'), ('manual', 'Manual'), ('manifesto', 'Manifesto')], default='manual', max_length=20)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('fornecedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equivalencias_produtos', to='cadastros.fornecedor')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equivalencias_fornecedor', to='produtos.produto')),
            ],
            options={
                'verbose_name': 'Equivalencia produto fornecedor',
                'verbose_name_plural': 'Equivalencias produto fornecedor',
                'db_table': 'produtos_fornecedores_equivalencias',
                'ordering': ['fornecedor_razao_social_xml', 'codigo_fornecedor', 'ean_utilizado'],
            },
        ),
        migrations.AddIndex(
            model_name='produtocodigobarras',
            index=models.Index(fields=['ean', 'ativo'], name='prod_cod_barras_ean_ativo_idx'),
        ),
        migrations.AddIndex(
            model_name='produtocodigobarras',
            index=models.Index(fields=['produto', 'ativo'], name='prod_cod_barras_prod_ativo_idx'),
        ),
        migrations.AddIndex(
            model_name='produtofornecedorequivalencia',
            index=models.Index(fields=['fornecedor', 'ativo'], name='prod_forn_eq_fornecedor_idx'),
        ),
        migrations.AddIndex(
            model_name='produtofornecedorequivalencia',
            index=models.Index(fields=['fornecedor_cnpj_xml', 'ativo'], name='prod_forn_eq_cnpj_idx'),
        ),
        migrations.AddIndex(
            model_name='produtofornecedorequivalencia',
            index=models.Index(fields=['ean_utilizado', 'ativo'], name='prod_forn_eq_ean_idx'),
        ),
        migrations.AddIndex(
            model_name='produtofornecedorequivalencia',
            index=models.Index(fields=['codigo_fornecedor', 'ativo'], name='prod_forn_eq_codigo_idx'),
        ),
    ]
