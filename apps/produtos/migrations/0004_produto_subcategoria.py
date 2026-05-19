# Generated manually to avoid unrelated migration prompts in producao.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0003_produto_wizard_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='subcategoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='produtos_subcategoria',
                to='produtos.categoriaproduto',
            ),
        ),
        migrations.AlterField(
            model_name='produto',
            name='tipo_produto',
            field=models.CharField(
                choices=[
                    ('unitario', 'Unidade'),
                    ('fracionado', 'Fracionado'),
                    ('granel_peso', 'Granel (peso)'),
                    ('granel_volume', 'Granel (volume)'),
                    ('granel_metragem', 'Granel (metragem)'),
                    ('servico', 'Servico'),
                    ('kit', 'Kit'),
                ],
                default='unitario',
                max_length=20,
            ),
        ),
    ]
