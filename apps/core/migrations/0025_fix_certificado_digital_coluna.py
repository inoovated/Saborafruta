"""
Correcao: as migrations 0011 e 0016 usavam SeparateDatabaseAndState com
database_operations=[] (ambas assumiam que a outra branch havia criado a
coluna), portanto a coluna nunca foi criada de fato no banco de dados.
Esta migration adiciona as colunas com IF NOT EXISTS para ser idempotente.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_cte'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE parametros_sistema
                    ADD COLUMN IF NOT EXISTS certificado_digital VARCHAR(500) NULL,
                    ADD COLUMN IF NOT EXISTS senha_certificado VARCHAR(255) NOT NULL DEFAULT '';
            """,
            reverse_sql="""
                ALTER TABLE parametros_sistema
                    DROP COLUMN IF EXISTS certificado_digital,
                    DROP COLUMN IF EXISTS senha_certificado;
            """,
        ),
    ]
