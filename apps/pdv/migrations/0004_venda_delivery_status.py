from django.db import migrations


class Migration(migrations.Migration):
    """Concilia as branches do PDV sem recriar campos de delivery.

    Os campos status_delivery, observacao_delivery e entregador já são
    criados em pdv.0002_venda_delivery_status.
    """

    dependencies = [
        ('pdv', '0003_alter_dispositivopdv_created_at_and_more'),
        ('pdv', '0002_venda_delivery_status'),
    ]

    operations = []
