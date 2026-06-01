from django.db import migrations, models


DIAS_SEMANA_TODOS = '0,1,2,3,4,5,6'


def mover_promocoes_para_vinculo_filial(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    ProdutoFilial = apps.get_model('produtos', 'ProdutoFilial')
    produtos_migrados = []
    for produto in Produto.objects.exclude(preco_promocional=0).iterator():
        ProdutoFilial.objects.update_or_create(
            produto_id=produto.pk,
            filial_id=produto.filial_id,
            defaults={
                'ativo': True,
                'preco_promocional': produto.preco_promocional,
                'promocao_tipo_desconto': produto.promocao_tipo_desconto or 'preco_final',
                'promocao_valor_desconto': produto.promocao_valor_desconto or 0,
                'promocao_inicio': produto.promocao_inicio,
                'promocao_fim': produto.promocao_fim,
                'promocao_dias_semana': produto.promocao_dias_semana or DIAS_SEMANA_TODOS,
            },
        )
        produtos_migrados.append(produto.pk)
    if produtos_migrados:
        Produto.objects.filter(pk__in=produtos_migrados).update(
            preco_promocional=0,
            promocao_tipo_desconto='preco_final',
            promocao_valor_desconto=0,
            promocao_inicio=None,
            promocao_fim=None,
            promocao_dias_semana=DIAS_SEMANA_TODOS,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0021_equivalencias_entrada'),
    ]

    operations = [
        migrations.AddField(
            model_name='produtofilial',
            name='preco_promocional',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='produtofilial',
            name='promocao_tipo_desconto',
            field=models.CharField(blank=True, default='preco_final', max_length=20),
        ),
        migrations.AddField(
            model_name='produtofilial',
            name='promocao_valor_desconto',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='produtofilial',
            name='promocao_inicio',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='produtofilial',
            name='promocao_fim',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='produtofilial',
            name='promocao_dias_semana',
            field=models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=20),
        ),
        migrations.RunPython(mover_promocoes_para_vinculo_filial, migrations.RunPython.noop),
    ]
