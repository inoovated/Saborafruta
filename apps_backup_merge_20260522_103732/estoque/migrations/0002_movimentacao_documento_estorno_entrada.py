from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimentacaoestoque',
            name='documento_tipo',
            field=models.CharField(blank=True, choices=[('pedido_venda', 'Pedido de Venda'), ('nfe', 'NF-e'), ('nfce', 'NFC-e'), ('outras_movimentacoes', 'Outras Movimentações'), ('inventario', 'Inventário'), ('transferencia', 'Transferência'), ('ajuste_manual', 'Ajuste Manual'), ('ordem_producao', 'Ordem de Produção'), ('estorno_entrada', 'Estorno de Entrada')], max_length=30),
        ),
    ]
