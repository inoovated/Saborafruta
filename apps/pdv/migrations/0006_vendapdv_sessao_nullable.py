from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("pdv", "0005_merge_20260522_1038"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vendapdv",
            name="sessao_pdv",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vendas",
                to="pdv.sessaopdv",
            ),
        ),
    ]
