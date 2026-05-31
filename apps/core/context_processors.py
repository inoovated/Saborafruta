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
        ('/produtos', 'Produtos', 'Cadastros', None, ''),
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
    screen_descriptions = {
        '/gestao/central': 'Acesse os principais atalhos administrativos e configuracoes do sistema.',
        '/gestao/usuarios': 'Gerencie usuarios, vinculos, permissoes e dados de acesso.',
        '/gestao/perfis': 'Organize perfis de acesso e regras de permissao por funcao.',
        '/gestao/empresas': 'Cadastre e acompanhe as empresas disponiveis no ambiente.',
        '/gestao/filiais': 'Controle filiais, dados operacionais e vinculos por empresa.',
        '/cadastros/clientes': 'Consulte, filtre e mantenha os dados comerciais dos clientes.',
        '/cadastros/fornecedores': 'Gerencie fornecedores usados em compras, estoque e fiscal.',
        '/cadastros/transportadoras': 'Cadastre transportadoras e informacoes de entrega.',
        '/cadastros/representantes': 'Acompanhe representantes e vinculos comerciais.',
        '/produtos/atualizacao-precos': 'Revise custos, margens e novos precos de venda por produto.',
        '/produtos/combos-promocoes': 'Monte combos e promocoes aplicadas ao catalogo de produtos.',
        '/produtos/fiscal': 'Configure NCM, CFOP, ICMS, PIS/COFINS e IPI dos produtos.',
        '/produtos/categorias': 'Organize categorias e subcategorias usadas no cadastro de produtos.',
        '/produtos/subcategorias': 'Refine a classificacao dos produtos dentro das categorias.',
        '/produtos/marcas': 'Cadastre marcas e fabricantes vinculados aos produtos.',
        '/produtos/unidades': 'Defina unidades de medida usadas no estoque e nas vendas.',
        '/produtos/tabelas-preco': 'Configure tabelas de preco para regras comerciais especificas.',
        '/produtos': 'Consulte, filtre e mantenha o catalogo de produtos e servicos.',
        '/estoque/sugestao-compras': 'Analise giro, demanda diaria e reposicao inteligente por produto.',
        '/estoque/reposicao': 'Acompanhe necessidades de reposicao e pontos de estoque.',
        '/estoque/movimentacoes': 'Registre e consulte entradas, saidas, ajustes e transferencias.',
        '/estoque/outras-movimentacoes': 'Acesse operacoes complementares de movimentacao de estoque.',
        '/estoque/lotes': 'Controle lotes, validade, rastreabilidade e saldos por produto.',
        '/estoque/inventarios': 'Organize contagens, divergencias e ajustes de inventario.',
        '/estoque/alertas': 'Monitore vencimentos, criticidade e pendencias de estoque.',
        '/estoque/relatorios': 'Analise saldos, custos e indicadores operacionais do estoque.',
        '/estoque': 'Acompanhe a operacao de estoque e seus principais atalhos.',
        '/compras/entradas': 'Controle notas de entrada, conferencia e etapas de recebimento.',
        '/compras/pedidos': 'Crie e acompanhe pedidos de compra junto aos fornecedores.',
        '/vendas/pedidos': 'Consulte e acompanhe pedidos de venda e seus status.',
        '/financeiro/receber': 'Gerencie titulos a receber, baixas, vencimentos e clientes.',
        '/financeiro/pagar': 'Gerencie titulos a pagar, baixas, vencimentos e fornecedores.',
        '/financeiro/formas-pagamento': 'Cadastre e ajuste formas de pagamento usadas nas operacoes.',
        '/financeiro/centros-custo': 'Organize centros de custo para rateio e analise financeira.',
        '/financeiro/plano-contas-despesas': 'Classifique despesas para controle gerencial e relatorios.',
        '/financeiro/plano-contas': 'Estruture contas financeiras usadas nas movimentacoes.',
        '/financeiro/documentos-fiscais': 'Acompanhe documentos fiscais vinculados ao financeiro.',
        '/financeiro/dre': 'Analise receitas, despesas e resultado operacional.',
        '/fiscal/manifesto/config': 'Ajuste parametros de consulta e manifesto de documentos fiscais.',
        '/fiscal/manifesto/anexar-xml': 'Anexe arquivos XML para leitura e processamento fiscal.',
        '/fiscal/manifesto': 'Consulte, manifeste e acompanhe documentos fiscais eletronicos.',
        '/fiscal/consultas/cnpj': 'Consulte dados cadastrais de empresas pelo CNPJ.',
        '/fiscal/consultas/ncm': 'Pesquise classificacoes fiscais NCM para produtos.',
        '/fiscal/consultas/cfop': 'Consulte CFOPs e naturezas de operacao.',
        '/fiscal/consultas/cnae': 'Pesquise atividades economicas por CNAE.',
        '/fiscal/consultas/municipios': 'Consulte municipios e codigos fiscais relacionados.',
        '/producao/ordens': 'Acompanhe ordens de producao, etapas e apontamentos.',
        '/producao/fichas-tecnicas': 'Mantenha composicoes e parametros tecnicos dos produtos.',
        '/qualidade': 'Registre e acompanhe analises, inspecoes e criterios de qualidade.',
        '/analytics/operacional': 'Visualize indicadores operacionais para tomada de decisao.',
        '/analytics/comercial': 'Acompanhe desempenho comercial, vendas e comportamento de clientes.',
        '/analytics/producao': 'Analise indicadores de producao, eficiencia e volume.',
        '/analytics/dre': 'Compare resultados financeiros em visao analitica.',
        '/lotes/alertas': 'Monitore alertas de vencimento e riscos por lote.',
        '/lotes/inspecoes': 'Registre inspecoes e resultados de controle por lote.',
        '/lotes/rastreabilidade': 'Acompanhe origem, destino e historico dos lotes.',
        '/lotes': 'Acesse indicadores e atalhos de controle de lotes.',
        '/': 'Acompanhe os principais indicadores e atalhos do sistema.',
    }
    module_descriptions = {
        'Gestao': 'Configure usuarios, permissoes e estrutura administrativa.',
        'Cadastros': 'Mantenha os dados base usados nas rotinas do sistema.',
        'Produtos': 'Gerencie o catalogo, classificacoes, precos e dados fiscais.',
        'Estoque': 'Controle saldos, movimentacoes, lotes e reposicao.',
        'Compras': 'Acompanhe pedidos, entradas e relacionamento com fornecedores.',
        'Vendas': 'Acompanhe pedidos, clientes e operacoes comerciais.',
        'Financeiro': 'Controle contas, pagamentos, recebimentos e resultados.',
        'Fiscal': 'Consulte e mantenha rotinas fiscais e documentos eletronicos.',
        'Producao': 'Controle fichas tecnicas, ordens e processos produtivos.',
        'Qualidade': 'Acompanhe analises e inspecoes de qualidade.',
        'Analytics': 'Analise indicadores gerenciais e operacionais.',
        'Lotes': 'Controle validade, rastreabilidade e inspecoes por lote.',
    }

    module_label, module_url = '', None
    for prefix, label, url in modules:
        if path.startswith(prefix):
            module_label, module_url = label, url
            break

    title, parent_label, parent_url, subtitle = 'Tela', module_label, module_url, ''
    for prefix, screen, parent, url, desc in screens:
        if path == prefix or path.startswith(prefix + '/'):
            title = screen
            parent_label = parent
            parent_url = url
            subtitle = desc or screen_descriptions.get(prefix, '')
            break
    if not subtitle:
        subtitle = module_descriptions.get(parent_label, 'Acompanhe e gerencie as informacoes desta tela.')

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
