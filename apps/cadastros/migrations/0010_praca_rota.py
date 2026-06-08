"""Migration: add Praca and Rota tables."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0009_motorista_add_cep_bairro_numero'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Praca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=100)),
                ('codigo', models.CharField(blank=True, help_text='Código interno da praça', max_length=20)),
                ('uf', models.CharField(blank=True, choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], max_length=2)),
                ('cidades', models.TextField(blank=True, help_text='Lista de cidades separadas por vírgula (ex: São Paulo, Guarulhos, Osasco)')),
                ('observacao', models.TextField(blank=True)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
            ],
            options={
                'verbose_name': 'Praça',
                'verbose_name_plural': 'Praças',
                'db_table': 'cadastros_pracas',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Rota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('nome', models.CharField(max_length=100)),
                ('codigo', models.CharField(blank=True, help_text='Código interno da rota', max_length=20)),
                ('descricao', models.TextField(blank=True)),
                ('motorista_padrao', models.CharField(blank=True, help_text='Nome do motorista padrão', max_length=100)),
                ('veiculo_padrao', models.CharField(blank=True, help_text='Placa do veículo padrão', max_length=20)),
                ('ativo', models.BooleanField(db_index=True, default=True)),
                ('filial', models.ForeignKey(db_index=True, help_text='Filial proprietária do registro', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.filial')),
                ('pracas', models.ManyToManyField(blank=True, related_name='rotas', to='cadastros.praca', verbose_name='Praças da rota')),
            ],
            options={
                'verbose_name': 'Rota',
                'verbose_name_plural': 'Rotas',
                'db_table': 'cadastros_rotas',
                'ordering': ['nome'],
            },
        ),
    ]
