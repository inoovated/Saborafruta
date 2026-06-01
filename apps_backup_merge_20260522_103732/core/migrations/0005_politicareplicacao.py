from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_usuario_foto_filial_imagem'),
    ]

    operations = [
        migrations.CreateModel(
            name='PoliticaReplicacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('replicar_clientes', models.BooleanField(default=False)),
                ('replicar_fornecedores', models.BooleanField(default=False)),
                ('replicar_produtos_basicos', models.BooleanField(default=False)),
                ('replicar_categorias', models.BooleanField(default=False)),
                ('replicar_unidades', models.BooleanField(default=False)),
                ('replicar_tabelas_preco', models.BooleanField(default=False)),
                ('replicar_preco_venda', models.BooleanField(default=False)),
                ('replicar_custo_base', models.BooleanField(default=False)),
                ('replicar_fiscal_basico', models.BooleanField(default=False)),
                ('replicar_ficha_tecnica', models.BooleanField(default=False)),
                ('replicar_transportadoras', models.BooleanField(default=False)),
                ('replicar_representantes', models.BooleanField(default=False)),
                ('perguntar_ao_salvar', models.BooleanField(default=False, help_text='Reservado para permitir escolha manual por cadastro em etapa futura.')),
                ('ativo', models.BooleanField(default=True)),
                ('empresa', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='politica_replicacao', to='core.empresa')),
            ],
            options={
                'verbose_name': 'PolÃ­tica de ReplicaÃ§Ã£o',
                'verbose_name_plural': 'PolÃ­ticas de ReplicaÃ§Ã£o',
                'db_table': 'politicas_replicacao',
            },
        ),
    ]
