from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0014_promocao_quantidade_condicao'),
    ]

    operations = [
        migrations.AddField(
            model_name='kitcategoria',
            name='dias_semana',
            field=models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=13),
        ),
        migrations.AddField(
            model_name='kitproduto',
            name='dias_semana',
            field=models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=13),
        ),
        migrations.AddField(
            model_name='produto',
            name='promocao_dias_semana',
            field=models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=13),
        ),
        migrations.AddField(
            model_name='promocaoquantidade',
            name='dias_semana',
            field=models.CharField(blank=True, default='0,1,2,3,4,5,6', max_length=13),
        ),
    ]
