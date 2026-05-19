from django.db import migrations


PROMO_ID_EXTERNO_TARGETS = [
    ('brindes_produtos', 'brindes_produtos_id_externo_a3f3181d'),
    ('kits_categorias', 'kits_categorias_id_externo_9a31d6fd'),
    ('kits_produtos', 'kits_produtos_id_externo_0116d302'),
    ('promocoes_quantidade', 'promocoes_quantidade_id_externo_13c9ab7f'),
]


def ensure_id_externo_columns(apps, schema_editor):
    connection = schema_editor.connection
    quote = schema_editor.quote_name

    for table_name, index_name in PROMO_ID_EXTERNO_TARGETS:
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            if table_name not in table_names:
                continue

            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table_name)
            }

        if 'id_externo' not in columns:
            schema_editor.execute(
                f"ALTER TABLE {quote(table_name)} "
                f"ADD COLUMN {quote('id_externo')} varchar(100) NOT NULL DEFAULT ''"
            )

        schema_editor.execute(
            f"CREATE INDEX IF NOT EXISTS {quote(index_name)} "
            f"ON {quote(table_name)} ({quote('id_externo')})"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0019_promocoes_id_externo'),
    ]

    operations = [
        migrations.RunPython(ensure_id_externo_columns, migrations.RunPython.noop),
    ]
