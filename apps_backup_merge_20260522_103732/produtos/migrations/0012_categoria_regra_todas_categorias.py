from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0011_combos_promocoes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kitcategoriaregra',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='kits_categoria',
                to='produtos.categoriaproduto',
            ),
        ),
    ]
