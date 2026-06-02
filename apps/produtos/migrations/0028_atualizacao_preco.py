# Generated manually for the price update workflow.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('compras', '0016_entradanfrateiofinanceiro_entradanfajustefinanceiro'),
        ('core', '0016_parametros_certificado_digital'),
        ('produtos', '0027_produto_rascunho_comercial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AtualizacaoPrecoLote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('origem', models.CharField(choices=[('avulsa', 'Uso avulso'), ('entrada_xml', 'Entrada XML')], default='avulsa', max_length=20)),
                ('numero_nfe', models.CharField(blank=True, max_length=30)),
                ('chave_nfe', models.CharField(blank=True, max_length=44)),
                ('fornecedor_nome', models.CharField(blank=True, max_length=180)),
                ('status', models.CharField(choices=[('rascunho', 'Rascunho'), ('simulado', 'Simulado'), ('aplicado', 'Aplicado'), ('cancelado', 'Cancelado')], default='rascunho', max_length=20)),
                ('regra_tipo', models.CharField(choices=[('percentual', 'Percentual'), ('valor_fixo', 'Valor fixo'), ('novo_preco', 'Novo preco'), ('markup', 'Markup'), ('margem', 'Margem')], default='percentual', max_length=20)),
                ('regra_config', models.JSONField(blank=True, default=dict)),
                ('filtros_config', models.JSONField(blank=True, default=dict)),
                ('total_produtos', models.PositiveIntegerField(default=0)),
                ('observacao', models.TextField(blank=True)),
                ('data_aplicacao', models.DateTimeField(blank=True, null=True)),
                ('entrada', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lotes_atualizacao_preco', to='compras.entradanf')),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lotes_atualizacao_preco', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Lote de atualizacao de preco',
                'verbose_name_plural': 'Lotes de atualizacao de preco',
                'db_table': 'produtos_atualizacao_preco_lotes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AtualizacaoPrecoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('preco_anterior', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('preco_novo', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('custo_base', models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ('margem_anterior', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('margem_nova', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('markup_anterior', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('markup_novo', models.DecimalField(decimal_places=4, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('simulado', 'Simulado'), ('aplicado', 'Aplicado'), ('bloqueado', 'Bloqueado'), ('erro', 'Erro')], default='simulado', max_length=20)),
                ('motivo_bloqueio', models.CharField(blank=True, max_length=255)),
                ('lote', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='produtos.atualizacaoprecolote')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='atualizacoes_preco', to='produtos.produto')),
            ],
            options={
                'verbose_name': 'Item de atualizacao de preco',
                'verbose_name_plural': 'Itens de atualizacao de preco',
                'db_table': 'produtos_atualizacao_preco_itens',
                'ordering': ['lote', 'produto__descricao'],
            },
        ),
        migrations.AddIndex(
            model_name='atualizacaoprecolote',
            index=models.Index(fields=['filial', 'origem', 'status'], name='prod_preco_lote_origem_idx'),
        ),
        migrations.AddIndex(
            model_name='atualizacaoprecolote',
            index=models.Index(fields=['entrada'], name='prod_preco_lote_entrada_idx'),
        ),
        migrations.AddIndex(
            model_name='atualizacaoprecoitem',
            index=models.Index(fields=['lote', 'status'], name='prod_preco_item_status_idx'),
        ),
        migrations.AddIndex(
            model_name='atualizacaoprecoitem',
            index=models.Index(fields=['produto'], name='prod_preco_item_produto_idx'),
        ),
    ]
