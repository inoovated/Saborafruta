from django.db import migrations


class Migration(migrations.Migration):
    """
    No ramo main, esta migration adicionava os campos delivery.
    No codigo atual eles sao adicionados por pdv.0002_venda_delivery_status,
    mas o banco Railway ja tem esta migration aplicada com os campos presentes.
    Dependencia em 0002_venda_delivery_status removida para evitar
    InconsistentMigrationHistory (Railway tem 0004 mas nao tinha 0002_delivery).
    A unificacao das branches fica por conta de pdv.0005_merge.
    """

    dependencies = [
        ('pdv', '0003_alter_dispositivopdv_created_at_and_more'),
    ]

    operations = []
