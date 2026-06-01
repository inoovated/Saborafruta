from django.db import migrations, models


def habilitar_venda_sem_estoque(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    Produto.objects.update(permite_venda_sem_estoque=True)


def reverter_venda_sem_estoque(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0004_produto_subcategoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='permite_venda_sem_estoque',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(
            habilitar_venda_sem_estoque,
            reverter_venda_sem_estoque,
        ),
    ]
