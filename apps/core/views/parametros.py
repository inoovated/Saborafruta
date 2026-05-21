"""Tela de Parâmetros do Sistema — identidade, contatos e configuração fiscal."""
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core.forms.parametros import FilialIdentidadeForm, ParametrosSistemaForm
from apps.core.models.parametros import ParametroDocumentoFiscal, ParametrosSistema
from apps.core.views._admin import admin_area_required

# Ordem em que as abas de documentos fiscais aparecem
ORDEM_DOCUMENTOS = ['nfe', 'nfce', 'cte', 'cte_os', 'mdfe', 'nfcom', 'nfse', 'nfse_nacional']


def _para_int(valor, padrao):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _garantir_documentos(params):
    """Garante que os 8 documentos fiscais existam, retornados na ordem definida."""
    existentes = {d.tipo_documento: d for d in params.documentos_fiscais.all()}
    documentos = []
    for tipo in ORDEM_DOCUMENTOS:
        doc = existentes.get(tipo)
        if doc is None:
            doc = ParametroDocumentoFiscal.objects.create(parametros=params, tipo_documento=tipo)
        documentos.append(doc)
    return documentos


@admin_area_required
def parametros_sistema(request):
    filial = getattr(request, 'filial_ativa', None)
    if filial is None:
        messages.error(request, 'Selecione uma filial para configurar os parâmetros.')
        return redirect('core:dashboard')

    params, _ = ParametrosSistema.objects.get_or_create(filial=filial)
    documentos = _garantir_documentos(params)

    if request.method == 'POST':
        form_filial = FilialIdentidadeForm(request.POST, instance=filial)
        form_params = ParametrosSistemaForm(request.POST, request.FILES, instance=params)
        if form_filial.is_valid() and form_params.is_valid():
            form_filial.save()
            params_salvos = form_params.save(commit=False)
            if request.POST.get('remover_logo') and params.logo:
                params.logo.delete(save=False)
                params_salvos.logo = None
            params_salvos.save()
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
                doc.save()
            messages.success(request, 'Parâmetros do sistema salvos com sucesso.')
            return redirect('core:admin_parametros')
        messages.error(request, 'Verifique os campos destacados e tente novamente.')
    else:
        form_filial = FilialIdentidadeForm(instance=filial)
        form_params = ParametrosSistemaForm(instance=params)

    return render(request, 'core/admin/parametros_form.html', {
        'title': 'Parâmetros do Sistema',
        'form_filial': form_filial,
        'form_params': form_params,
        'parametros': params,
        'documentos': documentos,
        # documentos que usam CFOP / natureza de operação
        'docs_com_cfop': {'nfe', 'nfce', 'cte', 'cte_os'},
    })
