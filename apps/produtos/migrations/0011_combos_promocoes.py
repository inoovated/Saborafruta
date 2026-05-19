import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_politicareplicacaofilial'),
        ('produtos', '0010_marca_produto_fornecedor'),
    ]

    operations = [
        migrations.CreateModel(
            name='KitCategoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('nome', models.CharField(max_length=120)),
                ('descricao', models.TextField(blank=True)),
                ('tipo_desconto', models.CharField(choices=[('preco_unitario', 'Preco unitario'), ('percentual', 'Percentual'), ('valor', 'Valor em R$'), ('preco_final', 'Preco final')], default='percentual', max_length=20)),
                ('valor_desconto', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('replicar_filiais', models.BooleanField(default=False)),
                ('permite_preco_promocional', models.BooleanField(default=False)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
            ],
            options={
                'db_table': 'kits_categorias',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='KitProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('nome', models.CharField(max_length=120)),
                ('descricao', models.TextField(blank=True)),
                ('tipo_desconto', models.CharField(choices=[('preco_unitario', 'Preco unitario'), ('percentual', 'Percentual'), ('valor', 'Valor em R$'), ('preco_final', 'Preco final')], default='percentual', max_length=20)),
                ('valor_desconto', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('replicar_filiais', models.BooleanField(default=False)),
                ('permite_preco_promocional', models.BooleanField(default=False)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
            ],
            options={
                'db_table': 'kits_produtos',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='PromocaoQuantidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('nome', models.CharField(max_length=120)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('replicar_filiais', models.BooleanField(default=False)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promocoes_quantidade', to='produtos.produto')),
            ],
            options={
                'db_table': 'promocoes_quantidade',
                'ordering': ['produto__descricao', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='KitCategoriaRegra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantidade_minima', models.DecimalField(decimal_places=3, default=1, max_digits=12)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='kits_categoria', to='produtos.categoriaproduto')),
                ('kit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regras', to='produtos.kitcategoria')),
                ('subcategoria', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='kits_subcategoria', to='produtos.categoriaproduto')),
            ],
            options={
                'db_table': 'kits_categorias_regras',
                'ordering': ['categoria__nome', 'subcategoria__nome'],
            },
        ),
        migrations.CreateModel(
            name='KitProdutoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantidade', models.DecimalField(decimal_places=3, default=1, max_digits=12)),
                ('kit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='produtos.kitproduto')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='kits_comerciais', to='produtos.produto')),
            ],
            options={
                'db_table': 'kits_produtos_itens',
                'ordering': ['produto__descricao'],
                'unique_together': {('kit', 'produto')},
            },
        ),
        migrations.CreateModel(
            name='PromocaoQuantidadeFaixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantidade_minima', models.DecimalField(decimal_places=3, max_digits=12)),
                ('tipo_desconto', models.CharField(choices=[('preco_unitario', 'Preco unitario'), ('percentual', 'Percentual'), ('valor', 'Valor em R$'), ('preco_final', 'Preco final')], default='preco_unitario', max_length=20)),
                ('valor', models.DecimalField(decimal_places=4, max_digits=14)),
                ('promocao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faixas', to='produtos.promocaoquantidade')),
            ],
            options={
                'db_table': 'promocoes_quantidade_faixas',
                'ordering': ['quantidade_minima'],
                'unique_together': {('promocao', 'quantidade_minima')},
            },
        ),
        migrations.AddIndex(
            model_name='kitcategoria',
            index=models.Index(fields=['filial', 'ativo'], name='kits_catego_filial__c3f7d0_idx'),
        ),
        migrations.AddIndex(
            model_name='kitcategoria',
            index=models.Index(fields=['data_inicio', 'data_fim'], name='kits_catego_data_in_18d8c6_idx'),
        ),
        migrations.AddIndex(
            model_name='kitproduto',
            index=models.Index(fields=['filial', 'ativo'], name='kits_produt_filial__abbb43_idx'),
        ),
        migrations.AddIndex(
            model_name='kitproduto',
            index=models.Index(fields=['data_inicio', 'data_fim'], name='kits_produt_data_in_7c1b07_idx'),
        ),
        migrations.AddIndex(
            model_name='promocaoquantidade',
            index=models.Index(fields=['filial', 'ativo'], name='promocoes_q_filial__34d9cb_idx'),
        ),
        migrations.AddIndex(
            model_name='promocaoquantidade',
            index=models.Index(fields=['data_inicio', 'data_fim'], name='promocoes_q_data_in_d9e665_idx'),
        ),
    ]
