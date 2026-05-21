from django.db import migrations, models
import django.db.models.deletion


def criar_vinculos_iniciais(apps, schema_editor):
    Cliente = apps.get_model('cadastros', 'Cliente')
    ClienteFilial = apps.get_model('cadastros', 'ClienteFilial')
    Fornecedor = apps.get_model('cadastros', 'Fornecedor')
    FornecedorFilial = apps.get_model('cadastros', 'FornecedorFilial')

    for cliente in Cliente.objects.exclude(filial_id__isnull=True).iterator():
        ClienteFilial.objects.get_or_create(
            cliente_id=cliente.pk,
            filial_id=cliente.filial_id,
            defaults={'ativo': True},
        )

    for fornecedor in Fornecedor.objects.exclude(filial_id__isnull=True).iterator():
        FornecedorFilial.objects.get_or_create(
            fornecedor_id=fornecedor.pk,
            filial_id=fornecedor.filial_id,
            defaults={'ativo': True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_politicareplicacao'),
        ('cadastros', '0003_grupos_replicacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='FornecedorFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fornecedores_vinculados', to='core.filial')),
                ('fornecedor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='cadastros.fornecedor')),
            ],
            options={
                'db_table': 'fornecedores_filiais',
                'ordering': ['fornecedor', 'filial'],
                'unique_together': {('fornecedor', 'filial')},
            },
        ),
        migrations.CreateModel(
            name='ClienteFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='cadastros.cliente')),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clientes_vinculados', to='core.filial')),
            ],
            options={
                'db_table': 'clientes_filiais',
                'ordering': ['cliente', 'filial'],
                'unique_together': {('cliente', 'filial')},
            },
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='fornecedorfilial',
            index=models.Index(fields=['filial', 'ativo'], name='fornecedor_f_filial_1fa82e_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='fornecedorfilial',
            index=models.Index(fields=['fornecedor', 'ativo'], name='fornecedor_f_fornece_98044f_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='clientefilial',
            index=models.Index(fields=['filial', 'ativo'], name='clientes_fi_filial_a9398f_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='clientefilial',
            index=models.Index(fields=['cliente', 'ativo'], name='clientes_fi_cliente_3eec06_idx'),
                ),
            ],
        ),
        migrations.RunPython(criar_vinculos_iniciais, migrations.RunPython.noop),
    ]
