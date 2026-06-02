from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0007_entrada_estorno_campos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entradanf',
            name='status',
            field=models.CharField(
                choices=[
                    ('rascunho', 'Rascunho'),
                    ('aguardando_vinculos', 'Aguardando vinculos'),
                    ('aguardando_conferencia', 'Aguardando conferencia'),
                    ('com_diferencas', 'Com diferencas'),
                    ('conferida', 'Conferida'),
                    ('processando', 'Processando'),
                    ('efetivada', 'Efetivada'),
                    ('cancelada', 'Cancelada'),
                    ('estornada', 'Cancelada'),
                ],
                db_index=True,
                default='rascunho',
                max_length=30,
            ),
        ),
        migrations.RemoveConstraint(
            model_name='entradanf',
            name='uniq_entrada_nf_chave_por_filial',
        ),
        migrations.AlterUniqueTogether(
            name='entradanf',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='entradanf',
            constraint=models.UniqueConstraint(
                fields=('fornecedor', 'numero_nf', 'serie_nf', 'filial'),
                condition=~models.Q(status__in=['cancelada', 'estornada']),
                name='uniq_entrada_nf_numero_fornecedor_ativa',
            ),
        ),
        migrations.AddConstraint(
            model_name='entradanf',
            constraint=models.UniqueConstraint(
                fields=('filial', 'chave_acesso_nf'),
                condition=(
                    ~models.Q(chave_acesso_nf='')
                    & ~models.Q(status__in=['cancelada', 'estornada'])
                ),
                name='uniq_entrada_nf_chave_por_filial',
            ),
        ),
    ]
