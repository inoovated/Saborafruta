from django.db import migrations, models
import django.db.models.deletion


def criar_vinculos_iniciais(apps, schema_editor):
    Transportadora = apps.get_model('cadastros', 'Transportadora')
    TransportadoraFilial = apps.get_model('cadastros', 'TransportadoraFilial')
    Representante = apps.get_model('cadastros', 'Representante')
    RepresentanteFilial = apps.get_model('cadastros', 'RepresentanteFilial')

    for transportadora in Transportadora.objects.exclude(filial_id__isnull=True).iterator():
        TransportadoraFilial.objects.get_or_create(
            transportadora_id=transportadora.pk,
            filial_id=transportadora.filial_id,
            defaults={'ativo': True},
        )

    for representante in Representante.objects.exclude(filial_id__isnull=True).iterator():
        RepresentanteFilial.objects.get_or_create(
            representante_id=representante.pk,
            filial_id=representante.filial_id,
            defaults={'ativo': True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_politicareplicacao'),
        ('cadastros', '0004_cadastro_filiais_vinculo'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransportadoraFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transportadoras_vinculadas', to='core.filial')),
                ('transportadora', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='cadastros.transportadora')),
            ],
            options={
                'db_table': 'transportadoras_filiais',
                'ordering': ['transportadora', 'filial'],
                'unique_together': {('transportadora', 'filial')},
            },
        ),
        migrations.CreateModel(
            name='RepresentanteFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='representantes_vinculados', to='core.filial')),
                ('representante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='cadastros.representante')),
            ],
            options={
                'db_table': 'representantes_filiais',
                'ordering': ['representante', 'filial'],
                'unique_together': {('representante', 'filial')},
            },
        ),
        migrations.AddIndex(
            model_name='transportadorafilial',
            index=models.Index(fields=['filial', 'ativo'], name='transportad_filial_abd7fb_idx'),
        ),
        migrations.AddIndex(
            model_name='transportadorafilial',
            index=models.Index(fields=['transportadora', 'ativo'], name='transportad_transpo_8a2d50_idx'),
        ),
        migrations.AddIndex(
            model_name='representantefilial',
            index=models.Index(fields=['filial', 'ativo'], name='representan_filial_641214_idx'),
        ),
        migrations.AddIndex(
            model_name='representantefilial',
            index=models.Index(fields=['representante', 'ativo'], name='representan_represe_e92d23_idx'),
        ),
        migrations.RunPython(criar_vinculos_iniciais, migrations.RunPython.noop),
    ]
