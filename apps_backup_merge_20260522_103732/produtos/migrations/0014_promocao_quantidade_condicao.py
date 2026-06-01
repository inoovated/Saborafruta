from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0013_kitcategoriaregra_desconto_por_regra'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='promocaoquantidadefaixa',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='promocaoquantidadefaixa',
            name='condicao_quantidade',
            field=models.CharField(
                choices=[('igual', 'Quantidade'), ('a_partir_de', 'A partir de')],
                default='igual',
                max_length=20,
            ),
        ),
        migrations.AlterUniqueTogether(
            name='promocaoquantidadefaixa',
            unique_together={('promocao', 'condicao_quantidade', 'quantidade_minima')},
        ),
    ]
