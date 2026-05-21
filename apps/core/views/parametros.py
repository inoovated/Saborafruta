"""System parameters screen: identity, contacts and fiscal setup."""
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core.forms.parametros import FilialIdentidadeForm, ParametrosSistemaForm
from apps.core.models.parametros import ParametroDocumentoFiscal, ParametrosSistema
from apps.core.views._admin import admin_area_required
from apps.fiscal.models import RegraFiscalUF, TabelaFiscalAuxiliar


ORDEM_DOCUMENTOS = ['nfe', 'nfce', 'cte', 'cte_os', 'mdfe', 'nfcom', 'nfse', 'nfse_nacional']
DOCS_COM_CFOP = {'nfe', 'nfce', 'cte', 'cte_os'}
DOCS_COM_NFE = {'nfe', 'nfce'}

TIPO_OPERACAO_CHOICES = [('1', 'Saida'), ('0', 'Entrada')]
FINALIDADE_NFE_CHOICES = [
    (1, 'Normal'),
    (2, 'Complementar'),
    (3, 'Ajuste'),
    (4, 'Devolucao'),
]
INDICADOR_DESTINO_CHOICES = [
    (1, 'Interna'),
    (2, 'Interestadual'),
    (3, 'Exterior'),
]
CONSUMIDOR_FINAL_CHOICES = [(0, 'Nao'), (1, 'Sim')]
PRESENCA_CHOICES = [
    (0, 'Nao se aplica'),
    (1, 'Presencial'),
    (2, 'Internet'),
    (3, 'Teleatendimento'),
    (4, 'NFC-e entrega em domicilio'),
    (5, 'Presencial fora do estabelecimento'),
    (9, 'Outros'),
]
MODALIDADE_FRETE_CHOICES = [
    (0, 'Emitente'),
    (1, 'Destinatario'),
    (2, 'Terceiros'),
    (3, 'Proprio remetente'),
    (4, 'Proprio destinatario'),
    (9, 'Sem frete'),
]


def _para_int(valor, padrao):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _digits(valor):
    return ''.join(ch for ch in (valor or '') if ch.isdigit())


def _garantir_documentos(params):
    existentes = {d.tipo_documento: d for d in params.documentos_fiscais.all()}
    documentos = []
    for tipo in ORDEM_DOCUMENTOS:
        doc = existentes.get(tipo)
        if doc is None:
            doc = ParametroDocumentoFiscal.objects.create(parametros=params, tipo_documento=tipo)
        documentos.append(doc)
    return documentos


def _logo_parametros_efetiva(filial, params):
    if params.logo:
        return params
    return (
        ParametrosSistema.objects
        .filter(filial__empresa=filial.empresa)
        .exclude(logo='').exclude(logo__isnull=True)
        .first()
    )


def _prontidao_fiscal(filial, params, documentos):
    regime = filial.regime_tributario or getattr(filial.empresa, 'regime_tributario', '')
    codigo_regime = (
        filial.codigo_regime_tributario
        or getattr(filial.empresa, 'codigo_regime_tributario', None)
    )
    nfce_habilitada = any(d.tipo_documento == 'nfce' and d.habilitado for d in documentos)
    checks = [
        {
            'label': 'CNPJ da filial',
            'ok': len(_digits(filial.cnpj)) == 14,
            'detail': 'Obrigatorio para autorizar documentos fiscais.',
        },
        {
            'label': 'Inscricao estadual',
            'ok': bool(filial.inscricao_estadual),
            'detail': 'Pode ser ISENTO quando a UF permitir.',
        },
        {
            'label': 'Endereco fiscal',
            'ok': all([filial.endereco, filial.numero, filial.bairro, filial.cidade, filial.uf, filial.cep]),
            'detail': 'Endereco completo evita rejeicao na SEFAZ.',
        },
        {
            'label': 'Codigo IBGE',
            'ok': bool(filial.codigo_municipio_ibge),
            'detail': 'Codigo do municipio usado no XML.',
        },
        {
            'label': 'Regime tributario',
            'ok': bool(regime and codigo_regime),
            'detail': 'Pode vir da filial ou do cadastro da empresa.',
        },
        {
            'label': 'Token Focus',
            'ok': bool(filial.focusnfe_token),
            'detail': 'Chave de integracao da filial com a Focus.',
        },
        {
            'label': 'Documento habilitado',
            'ok': any(d.habilitado for d in documentos),
            'detail': 'Marque Emissao habilitada na aba NF-e, NFC-e ou outro documento.',
        },
        {
            'label': 'CSC NFC-e',
            'ok': (not nfce_habilitada) or bool(params.nfce_csc_id and params.nfce_csc_token),
            'detail': 'Necessario quando NFC-e estiver habilitada.',
        },
    ]
    ok_count = sum(1 for item in checks if item['ok'])
    total = len(checks)
    return {
        'checks': checks,
        'ok_count': ok_count,
        'total': total,
        'percent': round((ok_count / total) * 100) if total else 0,
    }


def _status_tabelas_auxiliares():
    tipos = [
        (TabelaFiscalAuxiliar.Tipo.NCM, 'NCM'),
        (TabelaFiscalAuxiliar.Tipo.CEST, 'CEST'),
        (TabelaFiscalAuxiliar.Tipo.IPI_TIPI, 'IPI/TIPI'),
        (TabelaFiscalAuxiliar.Tipo.CST_PIS_COFINS, 'CST PIS/COFINS'),
        (TabelaFiscalAuxiliar.Tipo.CFOP, 'CFOPs'),
    ]
    itens = [
        {
            'label': label,
            'total': TabelaFiscalAuxiliar.objects.filter(tipo=tipo, ativo=True).count(),
        }
        for tipo, label in tipos
    ]
    itens.append({
        'label': 'Regras por UF',
        'total': RegraFiscalUF.objects.filter(ativo=True).count(),
    })
    total = sum(item['total'] for item in itens)
    return {
        'itens': itens,
        'total': total,
        'tem_base': total > 0,
    }


def _salvar_documentos(request, documentos):
    for doc in documentos:
        prefixo = f'doc_{doc.tipo_documento}_'
        doc.habilitado = bool(request.POST.get(prefixo + 'habilitado'))
        doc.serie = _para_int(request.POST.get(prefixo + 'serie'), doc.serie)
        doc.proximo_numero = _para_int(
            request.POST.get(prefixo + 'proximo_numero'), doc.proximo_numero,
        )
        doc.ambiente = _para_int(request.POST.get(prefixo + 'ambiente'), doc.ambiente)
        doc.cfop_padrao = (request.POST.get(prefixo + 'cfop_padrao') or '').strip()[:5]
        doc.natureza_operacao = (
            request.POST.get(prefixo + 'natureza_operacao') or ''
        ).strip()[:100]
        doc.tipo_operacao = (request.POST.get(prefixo + 'tipo_operacao') or doc.tipo_operacao or '1')[:1]
        doc.finalidade_nfe = _para_int(
            request.POST.get(prefixo + 'finalidade_nfe'), doc.finalidade_nfe,
        )
        doc.indicador_destino = _para_int(
            request.POST.get(prefixo + 'indicador_destino'), doc.indicador_destino,
        )
        doc.indicador_consumidor_final = _para_int(
            request.POST.get(prefixo + 'indicador_consumidor_final'),
            doc.indicador_consumidor_final,
        )
        doc.presenca_comprador = _para_int(
            request.POST.get(prefixo + 'presenca_comprador'), doc.presenca_comprador,
        )
        doc.modalidade_frete = _para_int(
            request.POST.get(prefixo + 'modalidade_frete'), doc.modalidade_frete,
        )
        doc.enviar_email = bool(request.POST.get(prefixo + 'enviar_email'))
        doc.informacoes_complementares = (
            request.POST.get(prefixo + 'informacoes_complementares') or ''
        ).strip()
        doc.save()


@admin_area_required
def parametros_sistema(request):
    filial = getattr(request, 'filial_ativa', None)
    if filial is None:
        messages.error(request, 'Selecione uma filial para configurar os parametros.')
        return redirect('core:dashboard')

    params, _ = ParametrosSistema.objects.get_or_create(filial=filial)
    documentos = _garantir_documentos(params)

    if request.method == 'POST':
        form_filial = FilialIdentidadeForm(request.POST, instance=filial)
        form_params = ParametrosSistemaForm(request.POST, request.FILES, instance=params)
        if form_filial.is_valid() and form_params.is_valid():
            form_filial.save()
            params_salvos = form_params.save(commit=False)
            remover_logo_id = request.POST.get('remover_logo')
            if remover_logo_id:
                logo_params = (
                    ParametrosSistema.objects
                    .filter(pk=remover_logo_id, filial__empresa=filial.empresa)
                    .first()
                )
                if logo_params and logo_params.logo:
                    logo_params.logo.delete(save=False)
                    logo_params.logo = None
                    if logo_params.pk == params.pk:
                        params_salvos.logo = None
                    else:
                        logo_params.save(update_fields=['logo', 'updated_at'])
            params_salvos.save()
            _salvar_documentos(request, documentos)
            messages.success(request, 'Parametros do sistema salvos com sucesso.')
            return redirect('core:admin_parametros')
        messages.error(request, 'Verifique os campos destacados e tente novamente.')
    else:
        form_filial = FilialIdentidadeForm(instance=filial)
        form_params = ParametrosSistemaForm(instance=params)

    return render(request, 'core/admin/parametros_form.html', {
        'title': 'Parametros do Sistema',
        'form_filial': form_filial,
        'form_params': form_params,
        'parametros': params,
        'logo_parametros': _logo_parametros_efetiva(filial, params),
        'documentos': documentos,
        'docs_com_cfop': DOCS_COM_CFOP,
        'docs_com_nfe': DOCS_COM_NFE,
        'tipo_operacao_choices': TIPO_OPERACAO_CHOICES,
        'finalidade_nfe_choices': FINALIDADE_NFE_CHOICES,
        'indicador_destino_choices': INDICADOR_DESTINO_CHOICES,
        'consumidor_final_choices': CONSUMIDOR_FINAL_CHOICES,
        'presenca_choices': PRESENCA_CHOICES,
        'modalidade_frete_choices': MODALIDADE_FRETE_CHOICES,
        'prontidao': _prontidao_fiscal(filial, params, documentos),
        'tabelas_auxiliares': _status_tabelas_auxiliares(),
    })
