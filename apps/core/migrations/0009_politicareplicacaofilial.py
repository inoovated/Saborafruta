from django.db import migrations, models
import django.db.models.deletion


CAMPOS_POLITICA = [
    'ativo',
    'replicar_clientes',
    'replicar_fornecedores',
    'replicar_produtos_basicos',
    'replicar_categorias',
    'replicar_marcas',
    'replicar_unidades',
    'replicar_tabelas_preco',
    'replicar_preco_venda',
    'replicar_custo_base',
    'replicar_fiscal_basico',
    'replicar_ficha_tecnica',
    'replicar_qualidade',
    'replicar_transportadoras',
    'replicar_representantes',
    'perguntar_ao_salvar',
]


def copiar_politicas_empresa_para_filiais(apps, schema_editor):
    Filial = apps.get_model('core', 'Filial')
    PoliticaReplicacao = apps.get_model('core', 'PoliticaReplicacao')
    PoliticaReplicacaoFilial = apps.get_model('core', 'PoliticaReplicacaoFilial')

    politicas_empresa = {
        politica.empresa_id: politica
        for politica in PoliticaReplicacao.objects.all()
    }
    for filial in Filial.objects.all():
        politica_empresa = politicas_empresa.get(filial.empresa_id)
        defaults = {'ativo': True}
        if politica_empresa:
            defaults = {
                campo: getattr(politica_empresa, campo, False)
                for campo in CAMPOS_POLITICA
            }
        PoliticaReplicacaoFilial.objects.get_or_create(
            filial_id=filial.pk,
            defaults=defaults,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_politicareplicacao_replicar_qualidade'),
    ]

    operations = [
        migrations.CreateModel(
            name='PoliticaReplicacaoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('replicar_clientes', models.BooleanField(default=False)),
                ('replicar_fornecedores', models.BooleanField(default=False)),
                ('replicar_produtos_basicos', models.BooleanField(default=False)),
                ('replicar_categorias', models.BooleanField(default=False)),
                ('replicar_marcas', models.BooleanField(default=False)),
                ('replicar_unidades', models.BooleanField(default=False)),
                ('replicar_tabelas_preco', models.BooleanField(default=False)),
                ('replicar_preco_venda', models.BooleanField(default=False)),
                ('replicar_custo_base', models.BooleanField(default=False)),
                ('replicar_fiscal_basico', models.BooleanField(default=False)),
                ('replicar_ficha_tecnica', models.BooleanField(default=False)),
                ('replicar_qualidade', models.BooleanField(default=False)),
                ('replicar_transportadoras', models.BooleanField(default=False)),
                ('replicar_representantes', models.BooleanField(default=False)),
                ('perguntar_ao_salvar', models.BooleanField(default=False, help_text='Reservado para permitir escolha manual por cadastro em etapa futura.')),
                ('ativo', models.BooleanField(default=True)),
                ('filial', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='politica_replicacao', to='core.filial')),
            ],
            options={
                'verbose_name': 'Politica de Replicacao por Filial',
                'verbose_name_plural': 'Politicas de Replicacao por Filial',
                'db_table': 'politicas_replicacao_filiais',
            },
        ),
        migrations.RunPython(copiar_politicas_empresa_para_filiais, migrations.RunPython.noop),
    ]
