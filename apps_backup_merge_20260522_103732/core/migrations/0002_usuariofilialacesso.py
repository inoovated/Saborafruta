from django.db import migrations, models
import django.db.models.deletion


def criar_acessos_iniciais(apps, schema_editor):
    Usuario = apps.get_model('core', 'Usuario')
    UsuarioFilialAcesso = apps.get_model('core', 'UsuarioFilialAcesso')

    for usuario in Usuario.objects.exclude(filial__isnull=True):
        UsuarioFilialAcesso.objects.update_or_create(
            usuario_id=usuario.pk,
            filial_id=usuario.filial_id,
            defaults={
                'perfil_id': usuario.perfil_id,
                'ativo': usuario.ativo,
                'is_padrao': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsuarioFilialAcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(default=True)),
                ('is_padrao', models.BooleanField(default=False)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos_usuarios', to='core.filial')),
                ('perfil', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='acessos_usuarios', to='core.perfilacesso')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos_filiais', to='core.usuario')),
            ],
            options={
                'verbose_name': 'Acesso do Usuario por Filial',
                'verbose_name_plural': 'Acessos dos Usuarios por Filial',
                'db_table': 'usuarios_filiais_acessos',
                'ordering': ['usuario__nome', 'filial__razao_social'],
                'unique_together': {('usuario', 'filial')},
            },
        ),
        migrations.RunPython(criar_acessos_iniciais, migrations.RunPython.noop),
    ]
