import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.financeiro.models.fiscal import DocumentoFiscal
from apps.fiscal.integrations.focusnfe import FocusNFeClient
from apps.fiscal.integrations.focusnfe.exceptions import FocusNFeError
from apps.fiscal.models import ManifestoFiscalConfig, ManifestoFiscalDocumento
from apps.fiscal.services.focusnfe_service import FocusNFeService, parse_ref
from apps.fiscal.services.manifesto_service import ManifestoFiscalService

logger = logging.getLogger(__name__)


class ManifestoFiscalListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    template_name = 'fiscal/manifesto/list.html'

    def get(self, request):
        documentos = ManifestoFiscalDocumento.objects.for_filial(request.filial_ativa).order_by('-created_at')
        page_obj = Paginator(documentos, 30).get_page(request.GET.get('page'))
        kpis = {
            'pendentes': documentos.filter(
                status_manifestacao=ManifestoFiscalDocumento.StatusManifestacao.NAO_MANIFESTADA,
            ).count(),
            'xml': documentos.filter(
                status_download_xml__in=[
                    ManifestoFiscalDocumento.StatusDownload.XML_DISPONIVEL,
                    ManifestoFiscalDocumento.StatusDownload.XML_BAIXADO,
                ],
            ).count(),
            'importadas': documentos.filter(
                status_download_xml=ManifestoFiscalDocumento.StatusDownload.IMPORTADA,
            ).count(),
        }
        config = ManifestoFiscalConfig.objects.for_filial(request.filial_ativa).filter(ativo=True).first()
        return render(request, self.template_name, {
            'documentos': page_obj.object_list,
            'page_obj': page_obj,
            'kpis': kpis,
            'config': config,
        })

    def post(self, request):
        messages.info(
            request,
            'Consulta DF-e real ainda esta preparada apenas em estrutura. Configure certificado para a proxima fase.',
        )
        return redirect('fiscal:manifesto-list')


class ManifestoFiscalConfigView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'
    template_name = 'fiscal/manifesto/config.html'

    def get(self, request):
        config, _ = ManifestoFiscalConfig.objects.get_or_create(
            filial=request.filial_ativa,
            cnpj=request.filial_ativa.cnpj,
            ambiente=ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
            defaults={'uf': request.filial_ativa.uf, 'ativo': True},
        )
        return render(request, self.template_name, {'config': config})

    def post(self, request):
        config, _ = ManifestoFiscalConfig.objects.get_or_create(
            filial=request.filial_ativa,
            cnpj=request.POST.get('cnpj') or request.filial_ativa.cnpj,
            ambiente=request.POST.get('ambiente') or ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
            defaults={'uf': request.POST.get('uf') or request.filial_ativa.uf, 'ativo': True},
        )
        config.uf = request.POST.get('uf') or request.filial_ativa.uf
        config.ultimo_nsu = request.POST.get('ultimo_nsu', '').strip()
        if request.FILES.get('certificado_digital'):
            config.certificado_digital = request.FILES['certificado_digital']
            config.certificado_nome = request.FILES['certificado_digital'].name
        config.save()
        messages.success(request, 'Configuracao do Manifesto Fiscal salva.')
        return redirect('fiscal:manifesto-config')


class ManifestoFiscalAcaoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'

    def post(self, request, pk, acao):
        documento = get_object_or_404(
            ManifestoFiscalDocumento.objects.for_filial(request.filial_ativa),
            pk=pk,
        )
        if acao == 'ciencia':
            ManifestoFiscalService.manifestar_ciencia(documento)
            messages.success(request, 'Ciencia registrada no ERP.')
        elif acao == 'desconhecer':
            ManifestoFiscalService.marcar_desconhecida(documento)
            messages.success(request, 'Operacao marcada como desconhecida.')
        elif acao == 'nao-realizada':
            ManifestoFiscalService.marcar_nao_realizada(documento)
            messages.success(request, 'Operacao marcada como nao realizada.')
        else:
            messages.error(request, 'Acao invalida.')
        return redirect('fiscal:manifesto-list')


# ===========================================================================
# Integração Focus NFe — Fase 1 (webhook + consultas auxiliares)
# ===========================================================================

@csrf_exempt
@require_POST
def webhook_focusnfe(request):
    """
    Recebe os callbacks de mudança de status da Focus NFe.

    Configure no painel da Focus a URL: /fiscal/webhook/focusnfe/?token=<TOKEN>
    onde <TOKEN> = ERP_FOCUSNFE_WEBHOOK_TOKEN das settings (opcional).
    """
    token_cfg = getattr(settings, 'ERP_FOCUSNFE_WEBHOOK_TOKEN', '')
    if token_cfg and request.GET.get('token') != token_cfg:
        return JsonResponse({'erro': 'token invalido'}, status=403)

    try:
        body = json.loads((request.body or b'{}').decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest('JSON invalido')

    ref = body.get('ref') or request.GET.get('ref', '')
    pk = parse_ref(ref)
    if not pk:
        return JsonResponse({'ok': True, 'ignorado': 'ref ausente ou invalida'})

    documento = DocumentoFiscal.objects.filter(pk=pk).first()
    if not documento:
        return JsonResponse({'ok': True, 'ignorado': 'documento nao encontrado'})

    try:
        FocusNFeService().aplicar_retorno(documento, body)
    except Exception:
        logger.exception('Erro ao processar webhook Focus NFe (ref=%s)', ref)
        return JsonResponse({'erro': 'falha ao processar'}, status=500)

    return JsonResponse({'ok': True, 'documento_id': documento.pk, 'status': documento.status})


def _consulta_focus(executar):
    """Executa uma consulta auxiliar tratando erros de configuração e API."""
    try:
        return JsonResponse(executar(FocusNFeClient()), safe=False)
    except ValueError as exc:  # token nao configurado
        return JsonResponse({'erro': str(exc)}, status=503)
    except FocusNFeError as exc:
        return JsonResponse(
            {'erro': str(exc), 'detalhe': exc.response_json},
            status=exc.status_code or 502,
        )


@login_required
@require_GET
def consulta_cnpj(request, valor):
    """Consulta dados cadastrais de um CNPJ."""
    return _consulta_focus(lambda c: c.cnpjs.consultar(valor))


@login_required
@require_GET
def consulta_ncm(request, valor):
    """Consulta um codigo NCM."""
    return _consulta_focus(lambda c: c.ncms.consultar(valor))


@login_required
@require_GET
def consulta_cfop(request, valor):
    """Consulta um codigo CFOP."""
    return _consulta_focus(lambda c: c.cfops.consultar(valor))


@login_required
@require_GET
def consulta_cnae(request, valor):
    """Consulta um codigo CNAE."""
    return _consulta_focus(lambda c: c.cnaes.consultar(valor))


@login_required
@require_GET
def consulta_municipios_api(request, valor):
    """Consulta um município pelo código IBGE."""
    return _consulta_focus(lambda c: c.municipios.consultar(valor))


# ===========================================================================
# Consultas Fiscais — páginas com interface
# ===========================================================================

def _get_pagina(request):
    try:
        return max(1, int(request.GET.get('pagina', 1)))
    except (TypeError, ValueError):
        return 1


def _focus_or_error(fn):
    """Executa fn(client) e retorna (dados, erro)."""
    try:
        return fn(FocusNFeClient()), None
    except ValueError as exc:
        return None, str(exc)
    except FocusNFeError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f'Erro inesperado: {exc}'


@login_required
def consultas_cfop(request):
    codigo = request.GET.get('codigo', '').strip()
    descricao = request.GET.get('descricao', '').strip()
    pagina = _get_pagina(request)
    resultados, erro = None, None

    if codigo:
        resultados, erro = _focus_or_error(lambda c: c.cfops.consultar(codigo))
        if isinstance(resultados, dict):
            resultados = [resultados]
    elif request.GET:
        resultados, erro = _focus_or_error(lambda c: c.cfops.listar(pagina=pagina))

    return render(request, 'fiscal/consultas/cfop.html', {
        'codigo': codigo,
        'descricao': descricao,
        'pagina': pagina,
        'resultados': resultados,
        'erro': erro,
    })


@login_required
def consultas_cnae(request):
    codigo = request.GET.get('codigo', '').strip()
    descricao = request.GET.get('descricao', '').strip()
    pagina = _get_pagina(request)
    resultados, erro = None, None

    if codigo:
        resultados, erro = _focus_or_error(lambda c: c.cnaes.consultar(codigo))
        if isinstance(resultados, dict):
            resultados = [resultados]
    elif descricao or request.GET.get('buscar'):
        resultados, erro = _focus_or_error(
            lambda c: c.cnaes.listar(descricao=descricao or None, pagina=pagina)
        )

    return render(request, 'fiscal/consultas/cnae.html', {
        'codigo': codigo,
        'descricao': descricao,
        'pagina': pagina,
        'resultados': resultados,
        'erro': erro,
    })


@login_required
def consultas_cnpj_page(request):
    cnpj = request.GET.get('cnpj', '').strip()
    resultado, erro = None, None

    if cnpj:
        resultado, erro = _focus_or_error(lambda c: c.cnpjs.consultar(cnpj))

    return render(request, 'fiscal/consultas/cnpj.html', {
        'cnpj': cnpj,
        'resultado': resultado,
        'erro': erro,
    })


@login_required
def consultas_ncm(request):
    codigo = request.GET.get('codigo', '').strip()
    descricao = request.GET.get('descricao', '').strip()
    pagina = _get_pagina(request)
    resultados, erro = None, None

    if codigo:
        resultados, erro = _focus_or_error(lambda c: c.ncms.consultar(codigo))
        if isinstance(resultados, dict):
            resultados = [resultados]
    elif descricao or request.GET.get('buscar'):
        resultados, erro = _focus_or_error(
            lambda c: c.ncms.listar(descricao=descricao or None, pagina=pagina)
        )

    return render(request, 'fiscal/consultas/ncm.html', {
        'codigo': codigo,
        'descricao': descricao,
        'pagina': pagina,
        'resultados': resultados,
        'erro': erro,
    })


@login_required
def consultas_municipios(request):
    uf = request.GET.get('uf', '').strip().upper()
    nome = request.GET.get('nome', '').strip()
    codigo_ibge = request.GET.get('codigo_ibge', '').strip()
    pagina = _get_pagina(request)
    resultados, erro = None, None

    if codigo_ibge:
        resultados, erro = _focus_or_error(lambda c: c.municipios.consultar(codigo_ibge))
        if isinstance(resultados, dict):
            resultados = [resultados]
    elif uf or nome or request.GET.get('buscar'):
        resultados, erro = _focus_or_error(
            lambda c: c.municipios.listar(
                uf=uf or None,
                nome=nome or None,
                pagina=pagina,
            )
        )

    return render(request, 'fiscal/consultas/municipios.html', {
        'uf': uf,
        'nome': nome,
        'codigo_ibge': codigo_ibge,
        'pagina': pagina,
        'resultados': resultados,
        'erro': erro,
    })
