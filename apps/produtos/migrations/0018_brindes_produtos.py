from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('produtos', '0017_produto_promocao_regra_viva'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrindeProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('nome', models.CharField(max_length=120)),
                ('descricao', models.TextField(blank=True)),
                ('quantidade_gatilho', models.DecimalField(decimal_places=3, default=1, max_digits=12)),
                ('data_inicio', models.DateField(blank=True, null=True)),
                ('data_fim', models.DateField(blank=True, null=True)),
                ('dias_semana', models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=13)),
                ('replicar_filiais', models.BooleanField(default=False)),
                ('permite_preco_promocional', models.BooleanField(default=True)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietaria do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
                ('produto_gatilho', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='brindes_gatilho', to='produtos.produto')),
            ],
            options={
                'db_table': 'brindes_produtos',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='BrindeProdutoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantidade', models.DecimalField(decimal_places=3, default=1, max_digits=12)),
                ('brinde', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='produtos.brindeproduto')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='brindes_recebidos', to='produtos.produto')),
            ],
            options={
                'db_table': 'brindes_produtos_itens',
                'ordering': ['produto__descricao'],
                'unique_together': {('brinde', 'produto')},
            },
        ),
        migrations.AddIndex(
            model_name='brindeproduto',
            index=models.Index(fields=['filial', 'ativo'], name='brindes_pro_filial__2ea672_idx'),
        ),
        migrations.AddIndex(
            model_name='brindeproduto',
            index=models.Index(fields=['data_inicio', 'data_fim'], name='brindes_pro_data_in_1ba8d7_idx'),
        ),
    ]
