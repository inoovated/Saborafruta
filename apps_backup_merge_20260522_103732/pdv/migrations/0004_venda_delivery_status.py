from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdv', '0003_alter_dispositivopdv_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendapdv',
            name='status_delivery',
            field=models.CharField(
                blank=True,
                choices=[
                    ('novo', 'Novo Pedido'),
                    ('preparando', 'Em Preparo'),
                    ('em_entrega', 'Saiu para Entrega'),
                    ('entregue', 'Entregue'),
                    ('cancelado', 'Cancelado'),
                ],
                default='novo',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='vendapdv',
            name='observacao_delivery',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='vendapdv',
            name='entregador',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
