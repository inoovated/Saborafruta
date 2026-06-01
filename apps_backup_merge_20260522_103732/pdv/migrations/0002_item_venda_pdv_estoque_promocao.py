from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pdv", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemvendapdv",
            name="custo_unitario_snapshot",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="itemvendapdv",
            name="preco_origem",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="itemvendapdv",
            name="preco_origem_detalhe",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="itemvendapdv",
            name="estoque_baixado",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="itemvendapdv",
            name="movimentacoes_estoque_ids",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
