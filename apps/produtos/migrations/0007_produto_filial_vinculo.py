from django.db import migrations, models
import django.db.models.deletion


def _atualizar_fk_produto(apps, produto_origem_id, produto_destino_id):
    Produto = apps.get_model('produtos', 'Produto')
    for modelo in apps.get_models():
        for campo in modelo._meta.get_fields():
            if not getattr(campo, 'many_to_one', False):
                continue
            modelo_relacionado = getattr(campo.remote_field, 'model', None)
            if modelo_relacionado is None:
                continue
            if getattr(modelo_relacionado._meta, 'label_lower', '') != Produto._meta.label_lower:
                continue
            try:
                modelo.objects.filter(**{campo.attname: produto_origem_id}).update(
                    **{campo.attname: produto_destino_id},
                )
            except Exception:
                pass


def criar_vinculos_produtos(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    ProdutoFilial = apps.get_model('produtos', 'ProdutoFilial')

    for produto in Produto.objects.filter(id_externo='').iterator():
        produto.id_externo = f'produto:{produto.pk}'
        produto.save(update_fields=['id_externo'])

    grupos = {}
    for produto in Produto.objects.exclude(filial_id__isnull=True).order_by('id').iterator():
        chave = produto.id_externo or f'produto:{produto.pk}'
        grupos.setdefault(chave, []).append(produto)

    for produtos in grupos.values():
        principal = produtos[0]
        ProdutoFilial.objects.get_or_create(
            produto_id=principal.pk,
            filial_id=principal.filial_id,
            defaults={'ativo': True},
        )
        for produto in produtos[1:]:
            ProdutoFilial.objects.get_or_create(
                produto_id=principal.pk,
                filial_id=produto.filial_id,
                defaults={'ativo': True},
            )
            _atualizar_fk_produto(apps, produto.pk, principal.pk)
            try:
                produto.delete()
            except Exception:
                pass


def remover_vinculos_produtos(apps, schema_editor):
    ProdutoFilial = apps.get_model('produtos', 'ProdutoFilial')
    ProdutoFilial.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_initial'),
        ('compras', '0001_initial'),
        ('estoque', '0001_initial'),
        ('financeiro', '0002_initial'),
        ('pdv', '0001_initial'),
        ('producao', '0001_initial'),
        ('produtos', '0006_categoria_filial'),
        ('vendas', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProdutoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produtos_vinculados', to='core.filial')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.produto')),
            ],
            options={
                'db_table': 'produtos_filiais',
                'ordering': ['produto', 'filial'],
                'unique_together': {('produto', 'filial')},
            },
        ),
        migrations.AddIndex(
            model_name='produtofilial',
            index=models.Index(fields=['filial', 'ativo'], name='produtos_fi_filial_9dc218_idx'),
        ),
        migrations.AddIndex(
            model_name='produtofilial',
            index=models.Index(fields=['produto', 'ativo'], name='produtos_fi_produto_c92e9f_idx'),
        ),
        migrations.RunPython(criar_vinculos_produtos, remover_vinculos_produtos),
    ]
