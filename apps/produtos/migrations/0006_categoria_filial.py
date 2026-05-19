from django.db import migrations, models
import django.db.models.deletion


def distribuir_categorias_por_filial(apps, schema_editor):
    CategoriaProduto = apps.get_model('produtos', 'CategoriaProduto')
    Produto = apps.get_model('produtos', 'Produto')
    Filial = apps.get_model('core', 'Filial')

    empresa_ids = (
        CategoriaProduto.objects
        .filter(filial__isnull=True)
        .values_list('empresa_id', flat=True)
        .distinct()
    )

    for empresa_id in empresa_ids:
        filiais = list(
            Filial.objects
            .filter(empresa_id=empresa_id, ativo=True)
            .order_by('-is_matriz', 'id')
        )
        if not filiais:
            continue

        categorias = list(
            CategoriaProduto.objects
            .filter(empresa_id=empresa_id, filial__isnull=True)
            .order_by('categoria_pai_id', 'id')
        )
        if not categorias:
            continue

        origem = filiais[0]
        mapping = {}
        for categoria in categorias:
            if not categoria.id_externo:
                categoria.id_externo = f'categoria:{categoria.id}'
            categoria.filial_id = origem.id
            categoria.save(update_fields=['id_externo', 'filial'])
            mapping[(categoria.id, origem.id)] = categoria

        for filial in filiais[1:]:
            pendentes = categorias[:]
            while pendentes:
                avancou = False
                for categoria in pendentes[:]:
                    parent = None
                    if categoria.categoria_pai_id:
                        parent = mapping.get((categoria.categoria_pai_id, filial.id))
                        if parent is None:
                            continue
                    clone, _ = CategoriaProduto.objects.get_or_create(
                        empresa_id=empresa_id,
                        filial_id=filial.id,
                        categoria_pai=parent,
                        nome=categoria.nome,
                        defaults={
                            'descricao': categoria.descricao,
                            'ativo': categoria.ativo,
                            'id_externo': categoria.id_externo,
                        },
                    )
                    clone.descricao = categoria.descricao
                    clone.ativo = categoria.ativo
                    clone.id_externo = categoria.id_externo
                    clone.save(update_fields=['descricao', 'ativo', 'id_externo'])
                    mapping[(categoria.id, filial.id)] = clone
                    pendentes.remove(categoria)
                    avancou = True
                if not avancou:
                    break

        ids_origem = {categoria.id for categoria in categorias}
        for produto in Produto.objects.filter(filial__empresa_id=empresa_id).iterator():
            update_fields = []
            if produto.categoria_id in ids_origem:
                destino = mapping.get((produto.categoria_id, produto.filial_id))
                if destino and produto.categoria_id != destino.id:
                    produto.categoria_id = destino.id
                    update_fields.append('categoria')
            if produto.subcategoria_id in ids_origem:
                destino = mapping.get((produto.subcategoria_id, produto.filial_id))
                if destino and produto.subcategoria_id != destino.id:
                    produto.subcategoria_id = destino.id
                    update_fields.append('subcategoria')
            if update_fields:
                produto.save(update_fields=update_fields)


def voltar_categorias_compartilhadas(apps, schema_editor):
    CategoriaProduto = apps.get_model('produtos', 'CategoriaProduto')
    CategoriaProduto.objects.update(filial=None)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('core', '0006_filial_participa_replicacao'),
        ('produtos', '0005_permite_venda_sem_estoque_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoriaproduto',
            name='filial',
            field=models.ForeignKey(
                blank=True,
                help_text='Filial proprietaria da categoria',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='categorias_produto',
                to='core.filial',
            ),
        ),
        migrations.AddField(
            model_name='categoriaproduto',
            name='id_externo',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name='categoriaproduto',
            unique_together={('empresa', 'filial', 'categoria_pai', 'nome')},
        ),
        migrations.AddIndex(
            model_name='categoriaproduto',
            index=models.Index(fields=['empresa', 'filial', 'ativo'], name='categorias__empresa_9f6672_idx'),
        ),
        migrations.AddIndex(
            model_name='categoriaproduto',
            index=models.Index(fields=['empresa', 'filial', 'categoria_pai'], name='categorias__empresa_94c86e_idx'),
        ),
        migrations.RunPython(distribuir_categorias_por_filial, voltar_categorias_compartilhadas),
    ]
