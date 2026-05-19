from decimal import Decimal, InvalidOperation
from datetime import date

from django.db import migrations, models


DIAS_SEMANA_TODOS = '0,1,2,3,4,5,6'


def _decimal(valor):
    try:
        return Decimal(str(valor or '0').replace(',', '.'))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def _date(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except (ValueError, TypeError):
        return None


def marcar_estado_promocional(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    ProdutoFilial = apps.get_model('produtos', 'ProdutoFilial')
    LogSistema = apps.get_model('core', 'LogSistema')

    ProdutoFilial.objects.update(preco_promocional_ativo=True)

    tabelas = {
        Produto._meta.db_table: Produto,
        ProdutoFilial._meta.db_table: ProdutoFilial,
    }
    logs = (
        LogSistema.objects
        .filter(tabela_afetada__in=tabelas.keys(), acao='editar')
        .order_by('data_hora', 'pk')
    )
    for log in logs:
        anteriores = log.dados_anteriores or {}
        novos = log.dados_novos or {}
        if 'preco_promocional' not in novos and 'promocao_ativa' not in novos:
            continue
        model = tabelas.get(log.tabela_afetada)
        if not model or not log.registro_id:
            continue
        try:
            obj = model.objects.get(pk=log.registro_id)
        except model.DoesNotExist:
            continue

        preco_anterior = _decimal(anteriores.get('preco_promocional'))
        preco_novo = _decimal(novos.get('preco_promocional'))
        ativa = novos.get('preco_promocional_ativo')
        if ativa is None:
            ativa = novos.get('promocao_ativa')
        if isinstance(ativa, str):
            ativa = ativa.lower() not in {'false', '0', 'nao', 'não'}
        elif ativa is None:
            ativa = not (preco_anterior > 0 and preco_novo <= 0)

        if not hasattr(obj, 'preco_promocional_ativo'):
            continue
        obj.preco_promocional_ativo = bool(ativa)
        update_fields = ['preco_promocional_ativo']
        if not obj.preco_promocional_ativo and (obj.preco_promocional or Decimal('0')) <= 0 and preco_anterior > 0:
            obj.preco_promocional = preco_anterior
            obj.promocao_tipo_desconto = anteriores.get('promocao_tipo_desconto') or 'preco_final'
            obj.promocao_valor_desconto = _decimal(anteriores.get('promocao_valor_desconto')) or preco_anterior
            obj.promocao_inicio = _date(anteriores.get('promocao_inicio'))
            obj.promocao_fim = _date(anteriores.get('promocao_fim'))
            obj.promocao_dias_semana = anteriores.get('promocao_dias_semana') or DIAS_SEMANA_TODOS
            update_fields.extend([
                'preco_promocional',
                'promocao_tipo_desconto',
                'promocao_valor_desconto',
                'promocao_inicio',
                'promocao_fim',
                'promocao_dias_semana',
            ])
        obj.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_politicareplicacaofilial'),
        ('produtos', '0022_produtofilial_promocao'),
    ]

    operations = [
        migrations.AddField(
            model_name='produtofilial',
            name='preco_promocional_ativo',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(marcar_estado_promocional, migrations.RunPython.noop),
    ]
