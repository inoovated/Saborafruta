from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_usuariofilialacesso'),
    ]

    operations = [
        migrations.AlterField(
            model_name='permissao',
            name='modulo',
            field=models.CharField(
                choices=[
                    ('vendas', 'Vendas'),
                    ('estoque', 'Estoque'),
                    ('financeiro', 'Financeiro'),
                    ('fiscal', 'Fiscal'),
                    ('config', 'Configurações'),
                    ('relatorios', 'Relatórios'),
                    ('pdv', 'PDV'),
                    ('producao', 'Produção'),
                    ('qualidade', 'Qualidade'),
                    ('compras', 'Compras'),
                    ('cadastros', 'Cadastros'),
                    ('produtos', 'Produtos'),
                ],
                max_length=60,
            ),
        ),
    ]
