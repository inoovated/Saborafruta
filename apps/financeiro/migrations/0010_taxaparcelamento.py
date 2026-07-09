from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0009_rename_fin_credcli_filial_idx_financeiro__filial__2a5b32_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxaParcelamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parcelas', models.PositiveSmallIntegerField()),
                ('taxa', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('forma_pagamento', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='taxas_parcelamento',
                    to='financeiro.formapagamento',
                )),
            ],
            options={
                'db_table': 'taxa_parcelamento',
                'ordering': ['parcelas'],
                'unique_together': {('forma_pagamento', 'parcelas')},
            },
        ),
    ]
