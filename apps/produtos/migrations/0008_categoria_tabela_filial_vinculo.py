from django.db import migrations, models
import django.db.models.deletion


def _atualizar_fk(apps, model_label, origem_id, destino_id):
    alvo = apps.get_model(*model_label.split('.'))
    for modelo in apps.get_models():
        for campo in modelo._meta.get_fields():
            if not getattr(campo, 'many_to_one', False):
                continue
            modelo_relacionado = getattr(campo.remote_field, 'model', None)
            if modelo_relacionado is None:
                continue
            if getattr(modelo_relacionado._meta, 'label_lower', '') != alvo._meta.label_lower:
                continue
            try:
                modelo.objects.filter(**{campo.attname: origem_id}).update(
                    **{campo.attname: destino_id},
                )
            except Exception:
                pass


def criar_vinculos_categorias(apps, schema_editor):
    CategoriaProduto = apps.get_model('produtos', 'CategoriaProduto')
    CategoriaProdutoFilial = apps.get_model('produtos', 'CategoriaProdutoFilial')

    for categoria in CategoriaProduto.objects.filter(id_externo='').iterator():
        categoria.id_externo = f'categoria:{categoria.pk}'
        categoria.save(update_fields=['id_externo'])

    grupos = {}
    for categoria in CategoriaProduto.objects.exclude(filial_id__isnull=True).order_by('categoria_pai_id', 'id').iterator():
        chave = categoria.id_externo or f'categoria:{categoria.pk}'
        grupos.setdefault(chave, []).append(categoria)

    mapa = {}
    for categorias in grupos.values():
        principal = categorias[0]
        CategoriaProdutoFilial.objects.get_or_create(
            categoria_id=principal.pk,
            filial_id=principal.filial_id,
            defaults={'ativo': True},
        )
        for categoria in categorias[1:]:
            mapa[categoria.pk] = principal.pk
            CategoriaProdutoFilial.objects.get_or_create(
                categoria_id=principal.pk,
                filial_id=categoria.filial_id,
                defaults={'ativo': True},
            )

    for origem_id, destino_id in mapa.items():
        _atualizar_fk(apps, 'produtos.CategoriaProduto', origem_id, destino_id)

    CategoriaProduto.objects.filter(pk__in=mapa.keys()).delete()


def criar_vinculos_tabelas(apps, schema_editor):
    TabelaPreco = apps.get_model('produtos', 'TabelaPreco')
    TabelaPrecoFilial = apps.get_model('produtos', 'TabelaPrecoFilial')
    ItemTabelaPreco = apps.get_model('produtos', 'ItemTabelaPreco')

    grupos = {}
    qs = TabelaPreco.objects.select_related('filial').exclude(filial_id__isnull=True).order_by('id')
    for tabela in qs.iterator():
        chave = (tabela.filial.empresa_id, tabela.descricao.strip().lower(), tabela.tipo)
        grupos.setdefault(chave, []).append(tabela)

    for tabelas in grupos.values():
        principal = tabelas[0]
        TabelaPrecoFilial.objects.get_or_create(
            tabela_id=principal.pk,
            filial_id=principal.filial_id,
            defaults={'ativo': True},
        )
        for tabela in tabelas[1:]:
            TabelaPrecoFilial.objects.get_or_create(
                tabela_id=principal.pk,
                filial_id=tabela.filial_id,
                defaults={'ativo': True},
            )
            for item in ItemTabelaPreco.objects.filter(tabela_id=tabela.pk).iterator():
                ItemTabelaPreco.objects.update_or_create(
                    tabela_id=principal.pk,
                    produto_id=item.produto_id,
                    quantidade_minima=item.quantidade_minima,
                    defaults={
                        'preco_unitario': item.preco_unitario,
                        'desconto_maximo': item.desconto_maximo,
                    },
                )
            _atualizar_fk(apps, 'produtos.TabelaPreco', tabela.pk, principal.pk)
            try:
                tabela.delete()
            except Exception:
                pass


def remover_vinculos(apps, schema_editor):
    apps.get_model('produtos', 'CategoriaProdutoFilial').objects.all().delete()
    apps.get_model('produtos', 'TabelaPrecoFilial').objects.all().delete()


def criar_vinculos(apps, schema_editor):
    criar_vinculos_categorias(apps, schema_editor)
    criar_vinculos_tabelas(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0007_produto_filial_vinculo'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaProdutoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.categoriaproduto')),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias_produto_vinculadas', to='core.filial')),
            ],
            options={
                'db_table': 'categorias_produto_filiais',
                'ordering': ['categoria', 'filial'],
                'unique_together': {('categoria', 'filial')},
            },
        ),
        migrations.CreateModel(
            name='TabelaPrecoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tabelas_preco_vinculadas', to='core.filial')),
                ('tabela', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.tabelapreco')),
            ],
            options={
                'db_table': 'tabelas_preco_filiais',
                'ordering': ['tabela', 'filial'],
                'unique_together': {('tabela', 'filial')},
            },
        ),
        migrations.AddIndex(
            model_name='categoriaprodutofilial',
            index=models.Index(fields=['filial', 'ativo'], name='categorias__filial_55c3c7_idx'),
        ),
        migrations.AddIndex(
            model_name='categoriaprodutofilial',
            index=models.Index(fields=['categoria', 'ativo'], name='categorias__categor_693f3c_idx'),
        ),
        migrations.AddIndex(
            model_name='tabelaprecofilial',
            index=models.Index(fields=['filial', 'ativo'], name='tabelas_pre_filial_4fd776_idx'),
        ),
        migrations.AddIndex(
            model_name='tabelaprecofilial',
            index=models.Index(fields=['tabela', 'ativo'], name='tabelas_pre_tabela__fa5248_idx'),
        ),
        migrations.RunPython(criar_vinculos, remover_vinculos),
    ]
