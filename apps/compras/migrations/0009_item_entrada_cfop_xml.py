from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0008_permite_reentrada_nf_cancelada'),
    ]

    operations = [
        migrations.AddField(
            model_name='itementradanf',
            name='cfop_xml',
            field=models.CharField(blank=True, default='', max_length=5),
        ),
    ]
