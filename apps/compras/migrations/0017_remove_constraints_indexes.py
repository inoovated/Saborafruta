"""
Migrations geradas automaticamente pelo Railway e aplicadas no banco.
Recriar aqui para manter consistência do histórico.
Usa RunSQL com IF EXISTS para ser idempotente.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0016_entradanfrateiofinanceiro_entradanfajustefinanceiro'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE entradas_nf DROP CONSTRAINT IF EXISTS uniq_entrada_nf_numero_fornecedor_ativa;",
                "ALTER TABLE entradas_nf DROP CONSTRAINT IF EXISTS uniq_entrada_nf_chave_por_filial;",
                "DROP INDEX IF EXISTS entrada_rateio_fin_pc_idx;",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
