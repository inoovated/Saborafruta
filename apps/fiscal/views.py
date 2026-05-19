from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.fiscal.models import ManifestoFiscalConfig, ManifestoFiscalDocumento
from apps.fiscal.services.manifesto_service import ManifestoFiscalService


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
