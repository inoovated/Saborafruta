from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_politicareplicacao_replicar_marcas"),
    ]

    operations = [
        migrations.AddField(
            model_name="politicareplicacao",
            name="replicar_qualidade",
            field=models.BooleanField(default=False),
        ),
    ]
