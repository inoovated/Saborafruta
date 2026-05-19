from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0015_dias_semana_promocoes'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocaoquantidade',
            name='usar_preco_promocional',
            field=models.BooleanField(default=True),
        ),
    ]
