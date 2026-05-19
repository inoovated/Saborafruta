from django.db import migrations, models
import uuid


def preencher_grupos(apps, schema_editor):
    Cliente = apps.get_model('cadastros', 'Cliente')
    Fornecedor = apps.get_model('cadastros', 'Fornecedor')
    for modelo in (Cliente, Fornecedor):
        for obj in modelo.objects.filter(grupo_replicacao__isnull=True).only('pk'):
            obj.grupo_replicacao = uuid.uuid4()
            obj.save(update_fields=['grupo_replicacao'])


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='grupo_replicacao',
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='fornecedor',
            name='grupo_replicacao',
            field=models.UUIDField(db_index=True, editable=False, null=True),
        ),
        migrations.RunPython(preencher_grupos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cliente',
            name='grupo_replicacao',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name='fornecedor',
            name='grupo_replicacao',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
    ]
