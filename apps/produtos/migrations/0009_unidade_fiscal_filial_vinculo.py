from django.db import migrations, models
import django.db.models.deletion


def _filiais_empresa(Filial, empresa_id):
    return Filial.objects.filter(empresa_id=empresa_id, ativo=True)


def criar_vinculos(apps, schema_editor):
    Filial = apps.get_model('core', 'Filial')
    UnidadeMedida = apps.get_model('produtos', 'UnidadeMedida')
    UnidadeMedidaFilial = apps.get_model('produtos', 'UnidadeMedidaFilial')
    ClasseFiscal = apps.get_model('produtos', 'ClasseFiscal')
    ClasseFiscalFilial = apps.get_model('produtos', 'ClasseFiscalFilial')
    NaturezaOperacao = apps.get_model('produtos', 'NaturezaOperacao')
    NaturezaOperacaoFilial = apps.get_model('produtos', 'NaturezaOperacaoFilial')

    for unidade in UnidadeMedida.objects.all().iterator():
        if not unidade.id_externo:
            unidade.id_externo = f'unidade:{unidade.pk}'
            unidade.save(update_fields=['id_externo'])
        for filial in _filiais_empresa(Filial, unidade.empresa_id).iterator():
            UnidadeMedidaFilial.objects.get_or_create(
                unidade_id=unidade.pk,
                filial_id=filial.pk,
                defaults={'ativo': True},
            )

    for classe in ClasseFiscal.objects.all().iterator():
        if not classe.id_externo:
            classe.id_externo = f'classe_fiscal:{classe.pk}'
            classe.save(update_fields=['id_externo'])
        for filial in _filiais_empresa(Filial, classe.empresa_id).iterator():
            ClasseFiscalFilial.objects.get_or_create(
                classe_fiscal_id=classe.pk,
                filial_id=filial.pk,
                defaults={'ativo': True},
            )

    for natureza in NaturezaOperacao.objects.all().iterator():
        if not natureza.id_externo:
            natureza.id_externo = f'natureza_operacao:{natureza.pk}'
            natureza.save(update_fields=['id_externo'])
        for filial in _filiais_empresa(Filial, natureza.empresa_id).iterator():
            NaturezaOperacaoFilial.objects.get_or_create(
                natureza_id=natureza.pk,
                filial_id=filial.pk,
                defaults={'ativo': True},
            )


def remover_vinculos(apps, schema_editor):
    apps.get_model('produtos', 'UnidadeMedidaFilial').objects.all().delete()
    apps.get_model('produtos', 'ClasseFiscalFilial').objects.all().delete()
    apps.get_model('produtos', 'NaturezaOperacaoFilial').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0008_categoria_tabela_filial_vinculo'),
    ]

    operations = [
        migrations.AddField(
            model_name='unidademedida',
            name='id_externo',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='classefiscal',
            name='id_externo',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name='naturezaoperacao',
            name='id_externo',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.CreateModel(
            name='UnidadeMedidaFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unidades_medida_vinculadas', to='core.filial')),
                ('unidade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.unidademedida')),
            ],
            options={
                'db_table': 'unidades_medida_filiais',
                'ordering': ['unidade', 'filial'],
                'unique_together': {('unidade', 'filial')},
            },
        ),
        migrations.CreateModel(
            name='ClasseFiscalFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('classe_fiscal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.classefiscal')),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes_fiscais_vinculadas', to='core.filial')),
            ],
            options={
                'db_table': 'classes_fiscais_filiais',
                'verbose_name': 'Classe Fiscal por Filial',
                'verbose_name_plural': 'Classes Fiscais por Filial',
                'unique_together': {('classe_fiscal', 'filial')},
            },
        ),
        migrations.CreateModel(
            name='NaturezaOperacaoFilial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='naturezas_operacao_vinculadas', to='core.filial')),
                ('natureza', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filiais_vinculo', to='produtos.naturezaoperacao')),
            ],
            options={
                'db_table': 'naturezas_operacao_filiais',
                'verbose_name': 'Natureza de Operacao por Filial',
                'verbose_name_plural': 'Naturezas de Operacao por Filial',
                'unique_together': {('natureza', 'filial')},
            },
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='unidademedidafilial',
            index=models.Index(fields=['filial', 'ativo'], name='unidades_me_filial_89870f_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='unidademedidafilial',
            index=models.Index(fields=['unidade', 'ativo'], name='unidades_me_unidade_889645_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='classefiscalfilial',
            index=models.Index(fields=['filial', 'ativo'], name='classes_fis_filial_80ebea_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='classefiscalfilial',
            index=models.Index(fields=['classe_fiscal', 'filial'], name='classes_fis_classe__d3a08a_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='naturezaoperacaofilial',
            index=models.Index(fields=['filial', 'ativo'], name='naturezas_o_filial_e913f2_idx'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddIndex(
            model_name='naturezaoperacaofilial',
            index=models.Index(fields=['natureza', 'filial'], name='naturezas_o_naturez_14c865_idx'),
                ),
            ],
        ),
        migrations.RunPython(criar_vinculos, remover_vinculos),
    ]
