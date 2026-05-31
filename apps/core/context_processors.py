"""Context processors: disponibilizam dados em todos os templates."""
from apps.core.models import Filial


def page_context(request):
    """Monta o caminho visual da tela para o cabecalho global."""
    path = (getattr(request, 'path', '') or '').rstrip('/') or '/'
    if path.startswith('/pdv'):
        return {'erp_page_context': None}

    modules = [
        ('/gestao', 'Gestão', '/gestao/central/'),
        ('/cadastros', 'Cadastros', None),
        ('/produtos', 'Produtos', '/produtos/'),
        ('/estoque', 'Estoque', '/estoque/'),
        ('/compras', 'Compras', None),
        ('/vendas', 'Vendas', None),
        ('/financeiro', 'Financeiro', None),
        ('/fiscal', 'Fiscal', None),
        ('/producao', 'Produção', None),
        ('/qualidade', 'Qualidade', None),
        ('/analytics', 'Analytics', None),
        ('/lotes', 'Lotes', '/lotes/'),
    ]
    screens = [
        ('/gestao/central', 'Central Administrativa', 'Gestão', '/gestao/central/', ''),
        ('/gestao/usuarios', 'Usuários', 'Gestão', '/gestao/central/', ''),
        ('/gestao/perfis', 'Perfis de acesso', 'Gestão', '/gestao/central/', ''),
        ('/gestao/empresas', 'Empresas', 'Gestão', '/gestao/central/', ''),
        ('/gestao/filiais', 'Filiais', 'Gestão', '/gestao/central/', ''),
        ('/cadastros/clientes', 'Clientes', 'Cadastros', None, ''),
        ('/cadastros/fornecedores', 'Fornecedores', 'Cadastros', None, ''),
        ('/cadastros/transportadoras', 'Transportadoras', 'Cadastros', None, ''),
        ('/cadastros/representantes', 'Representantes', 'Cadastros', None, ''),
        ('/produtos/atualizacao-precos', 'Atualização de preço de venda', 'Produtos', '/produtos/', ''),
        ('/produtos/combos-promocoes', 'Combos e Promoções', 'Produtos', '/produtos/', ''),
        ('/produtos/fiscal', 'Fiscal e tributário', 'Produtos', '/produtos/', ''),
        ('/produtos/categorias', 'Categorias', 'Produtos', '/produtos/', ''),
        ('/produtos/subcategorias', 'Subcategorias', 'Produtos', '/produtos/', ''),
        ('/produtos/marcas', 'Marcas / Fabricantes', 'Produtos', '/produtos/', ''),
        ('/produtos/unidades', 'Unidades de Medida', 'Produtos', '/produtos/', ''),
        ('/produtos/tabelas-preco', 'Tabelas de Preço', 'Produtos', '/produtos/', ''),
        ('/produtos', 'Produtos', 'Produtos', '/produtos/', ''),
        ('/estoque/sugestao-compras', 'Sugestão de Compras', 'Estoque', '/estoque/', 'Análise de giro, demanda diária e reposição inteligente por produto'),
        ('/estoque/reposicao', 'Reposição de estoque', 'Estoque', '/estoque/', ''),
        ('/estoque/movimentacoes', 'Movimentações de estoque', 'Estoque', '/estoque/', ''),
        ('/estoque/outras-movimentacoes', 'Outras Movimentações', 'Estoque', '/estoque/', ''),
        ('/estoque/lotes', 'Lotes', 'Estoque', '/estoque/', ''),
        ('/estoque/inventarios', 'Inventários', 'Estoque', '/estoque/', ''),
        ('/estoque/alertas', 'Alertas de Estoque', 'Estoque', '/estoque/', ''),
        ('/estoque/relatorios', 'Relatórios de estoque', 'Estoque', '/estoque/', ''),
        ('/estoque', 'Estoque', 'Estoque', '/estoque/', ''),
        ('/compras/entradas', 'Entrada de Mercadoria', 'Compras', None, ''),
        ('/compras/pedidos', 'Pedidos de Compra', 'Compras', None, ''),
        ('/vendas/pedidos', 'Pedidos de Venda', 'Vendas', None, ''),
        ('/financeiro/receber', 'Contas a Receber', 'Financeiro', None, ''),
        ('/financeiro/pagar', 'Contas a Pagar', 'Financeiro', None, ''),
        ('/financeiro/formas-pagamento', 'Formas de pagamento', 'Financeiro', None, ''),
        ('/financeiro/centros-custo', 'Centros de custo', 'Financeiro', None, ''),
        ('/financeiro/plano-contas-despesas', 'Plano de contas de despesas', 'Financeiro', None, ''),
        ('/financeiro/plano-contas', 'Plano de Contas', 'Financeiro', None, ''),
        ('/financeiro/documentos-fiscais', 'Documentos fiscais', 'Financeiro', None, ''),
        ('/financeiro/dre', 'DRE', 'Financeiro', None, ''),
        ('/fiscal/manifesto/config', 'Configuração DF-e', 'Fiscal', None, ''),
        ('/fiscal/manifesto/anexar-xml', 'Anexar XML', 'Fiscal', None, ''),
        ('/fiscal/manifesto', 'Manifesto Fiscal', 'Fiscal', None, ''),
        ('/fiscal/consultas/cnpj', 'Consulta CNPJ', 'Fiscal', None, ''),
        ('/fiscal/consultas/ncm', 'Consulta NCM', 'Fiscal', None, ''),
        ('/fiscal/consultas/cfop', 'Consulta CFOP', 'Fiscal', None, ''),
        ('/fiscal/consultas/cnae', 'Consulta CNAE', 'Fiscal', None, ''),
        ('/fiscal/consultas/municipios', 'Consulta Municípios', 'Fiscal', None, ''),
        ('/producao/ordens', 'Ordens de Produção', 'Produção', None, ''),
        ('/producao/fichas-tecnicas', 'Fichas Técnicas', 'Produção', None, ''),
        ('/qualidade', 'Qualidade', 'Qualidade', None, ''),
        ('/analytics/operacional', 'Analytics Operacional', 'Analytics', None, ''),
        ('/analytics/comercial', 'Analytics Comercial', 'Analytics', None, ''),
        ('/analytics/producao', 'Analytics Produção', 'Analytics', None, ''),
        ('/analytics/dre', 'Analytics DRE', 'Analytics', None, ''),
        ('/lotes/alertas', 'Alertas de vencimento', 'Lotes', '/lotes/', ''),
        ('/lotes/inspecoes', 'Inspeções de lote', 'Lotes', '/lotes/', ''),
        ('/lotes/rastreabilidade', 'Rastreabilidade', 'Lotes', '/lotes/', ''),
        ('/lotes', 'Dashboard de Lotes', 'Lotes', '/lotes/', ''),
        ('/', 'Dashboard', '', None, ''),
    ]

    module_label, module_url = '', None
    for prefix, label, url in modules:
        if path.startswith(prefix):
            module_label, module_url = label, url
            break

    title, parent_label, parent_url, subtitle = 'Tela', module_label, module_url, ''
    for prefix, screen, parent, url, desc in screens:
        if path == prefix or path.startswith(prefix + '/'):
            title, parent_label, parent_url, subtitle = screen, parent, url, desc
            break

    return {
        'erp_page_context': {
            'module': parent_label,
            'module_url': parent_url,
            'title': title,
            'subtitle': subtitle,
        }
    }


def parametros_sistema(request):
    """Injeta os parâmetros do sistema (logo) em todos os templates.

    Logado: usa a logo da filial ativa. Sem filial (ex.: tela de login):
    usa a primeira logo cadastrada como fallback.
    """
    from apps.core.models.parametros import ParametrosSistema
    params = None
    try:
        filial = getattr(request, 'filial_ativa', None)
        if filial is not None:
            params = ParametrosSistema.objects.filter(filial=filial).first()
        if params is None or not params.logo:
            fallback = (
                ParametrosSistema.objects
                .exclude(logo='').exclude(logo__isnull=True)
                .first()
            )
            if fallback is not None:
                params = fallback
    except Exception:
        params = None
    return {'parametros_sistema': params}


def filial_context(request):
    """Injeta filial ativa e filiais disponíveis em todos os templates."""
    ctx = {
        'filial_ativa': getattr(request, 'filial_ativa', None),
        'filiais_disponiveis': [],
    }
    if not request.user.is_authenticated:
        return ctx
    try:
        user = request.user
        qs = Filial.objects.filter(ativo=True)
        perfil = getattr(user, 'perfil', None)
        is_admin = user.is_superuser or (perfil is not None and perfil.is_admin)
        if user.is_superuser and ctx['filial_ativa']:
            qs = qs.filter(empresa_id=ctx['filial_ativa'].empresa_id)
        elif not user.is_superuser:
            qs = qs.filter(empresa=user.empresa)
        if not is_admin:
            acessos_ids = list(user.acessos_filiais.filter(ativo=True).values_list('filial_id', flat=True))
            if acessos_ids:
                qs = qs.filter(pk__in=acessos_ids)
            elif user.filial_id:
                qs = qs.filter(pk=user.filial_id)
        ctx['filiais_disponiveis'] = list(qs.order_by('nome_fantasia', 'razao_social'))
    except Exception:
        pass
    return ctx
