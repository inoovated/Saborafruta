from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0023_promocao_ativa_produto_filial'),
    ]

    operations = [
        migrations.AddField(
            model_name='produtofilial',
            name='preco_promocional_replicar_filiais',
            field=models.BooleanField(default=False),
        ),
    ]
