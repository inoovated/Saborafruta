# Generated manually to avoid unrelated migration prompts from other apps.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0005_transportadora_representante_filiais'),
        ('core', '0007_politicareplicacao_replicar_marcas'),
        ('produtos', '0009_unidade_fiscal_filial_vinculo'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarcaProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(blank=True)),
                ('id_externo', models.CharField(blank=True, db_index=True, max_length=100)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marcas_produto', to='core.empresa')),
                ('filial', models.ForeignKey(blank=True, help_text='Filial proprietaria da marca / fabricante', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='marcas_produto', to='core.filial')),
            ],
            options={
                'verbose_name': 'Marca / Fabricante',
                'verbose_name_plural': 'Marcas / Fabricantes',
                'db_table': 'marcas_produto',
                'ordering': ['nome'],
                'unique_together': {('empresa', 'filial', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='MarcaProdutoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marcas_produto_vinculadas', to='core.filial')),
                ('marca', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.marcaproduto')),
            ],
            options={
                'db_table': 'marcas_produto_filiais',
                'ordering': ['marca', 'filial'],
                'unique_together': {('marca', 'filial')},
            },
        ),
        migrations.AddField(
            model_name='produto',
            name='fornecedor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos', to='cadastros.fornecedor'),
        ),
        migrations.AddField(
            model_name='produto',
            name='marca',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos', to='produtos.marcaproduto'),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='marcaproduto',
            index=models.Index(fields=['empresa', 'filial', 'ativo'], name='marcas_prod_empresa_999378_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='marcaproduto',
            index=models.Index(fields=['empresa', 'filial', 'nome'], name='marcas_prod_empresa_28e4db_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='marcaprodutofilial',
            index=models.Index(fields=['filial', 'ativo'], name='marcas_prod_filial_5c4f35_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='marcaprodutofilial',
            index=models.Index(fields=['marca', 'ativo'], name='marcas_prod_marca_43d15b_idx'),
                ),
            ],
        ),
    ]
