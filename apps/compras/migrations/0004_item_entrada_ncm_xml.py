from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0003_entrada_recebimento_base'),
    ]

    operations = [
        migrations.AddField(
            model_name='itementradanf',
            name='ncm_xml',
            field=models.CharField(blank=True, db_index=True, max_length=8),
        ),
    ]
