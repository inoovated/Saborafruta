from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_parametros_fiscais_complementares'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistroAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('modulo', models.CharField(choices=[('compras', 'Compras'), ('estoque', 'Estoque'), ('financeiro', 'Financeiro')], db_index=True, max_length=40)),
                ('acao', models.CharField(choices=[('visualizar', 'Visualizar'), ('criar', 'Criar'), ('editar', 'Editar'), ('aprovar', 'Aprovar'), ('cancelar', 'Cancelar'), ('exportar', 'Exportar'), ('efetivar', 'Efetivar'), ('vincular', 'Vincular'), ('reprocessar', 'Reprocessar'), ('ajustar', 'Ajustar'), ('transferir', 'Transferir'), ('inventariar', 'Inventariar'), ('baixar_validade', 'Baixar validade')], db_index=True, max_length=40)),
                ('objeto_tipo', models.CharField(db_index=True, max_length=80)),
                ('objeto_id', models.BigIntegerField(db_index=True)),
                ('objeto_descricao', models.CharField(blank=True, max_length=255)),
                ('relacionado_tipo', models.CharField(blank=True, db_index=True, max_length=80)),
                ('relacionado_id', models.BigIntegerField(blank=True, db_index=True, null=True)),
                ('justificativa', models.TextField(blank=True)),
                ('dados_anteriores', models.JSONField(blank=True, null=True)),
                ('dados_novos', models.JSONField(blank=True, null=True)),
                ('metadados', models.JSONField(blank=True, null=True)),
                ('ip_acesso', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('filial', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_auditoria', to='core.filial')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registros_auditoria', to='core.usuario')),
            ],
            options={
                'verbose_name': 'Registro de auditoria',
                'verbose_name_plural': 'Registros de auditoria',
                'db_table': 'registros_auditoria',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['modulo', 'acao', '-criado_em'], name='registros_a_modulo_5a598c_idx'),
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['objeto_tipo', 'objeto_id', '-criado_em'], name='registros_a_objeto__7b5349_idx'),
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['relacionado_tipo', 'relacionado_id', '-criado_em'], name='registros_a_relacio_7c2b86_idx'),
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['usuario', '-criado_em'], name='registros_a_usuario_92638f_idx'),
        ),
        migrations.AddIndex(
            model_name='registroauditoria',
            index=models.Index(fields=['filial', '-criado_em'], name='registros_a_filial__c73f5f_idx'),
        ),
    ]
