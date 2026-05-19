from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.fiscal.integrations.dfe_client import avaliar_prontidao_dfe
from apps.fiscal.models import ManifestoFiscalConfig, ManifestoFiscalDocumento
from apps.fiscal.services.certificado_a1 import validar_certificado_a1_para_config
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
        try:
            resultado = ManifestoFiscalService.sincronizar_documentos(request.filial_ativa, request.user)
        except DomainError as exc:
            messages.error(request, str(exc))
            return redirect('fiscal:manifesto-list')

        if resultado.total_documentos:
            messages.success(
                request,
                (
                    f'Consulta DF-e concluida: {resultado.criados} novo(s), '
                    f'{resultado.atualizados} atualizado(s).'
                ),
            )
        else:
            messages.info(
                request,
                resultado.mensagem or 'Consulta DF-e executada em modo seguro; nenhum documento novo.',
            )
        return redirect('fiscal:manifesto-list')


class ManifestoFiscalConfigView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'editar'
    template_name = 'fiscal/manifesto/config.html'

    def get_context(self, config):
        return {
            'config': config,
            'prontidao': avaliar_prontidao_dfe(config),
        }

    def get(self, request):
        config, _ = ManifestoFiscalConfig.objects.get_or_create(
            filial=request.filial_ativa,
            cnpj=request.filial_ativa.cnpj,
            ambiente=ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
            defaults={'uf': request.filial_ativa.uf, 'ativo': True},
        )
        return render(request, self.template_name, self.get_context(config))

    def post(self, request):
        ambiente = request.POST.get('ambiente') or ManifestoFiscalConfig.Ambiente.HOMOLOGACAO
        if (
            ambiente == ManifestoFiscalConfig.Ambiente.PRODUCAO
            and not getattr(settings, 'FISCAL_ALLOW_PRODUCTION_ENVIRONMENT', False)
        ):
            config, _ = ManifestoFiscalConfig.objects.get_or_create(
                filial=request.filial_ativa,
                cnpj=request.POST.get('cnpj') or request.filial_ativa.cnpj,
                ambiente=ManifestoFiscalConfig.Ambiente.HOMOLOGACAO,
                defaults={'uf': request.POST.get('uf') or request.filial_ativa.uf, 'ativo': True},
            )
            messages.error(
                request,
                'Ambiente de producao bloqueado por seguranca. Use homologacao por enquanto.',
            )
            return render(request, self.template_name, self.get_context(config))

        config, _ = ManifestoFiscalConfig.objects.get_or_create(
            filial=request.filial_ativa,
            cnpj=request.POST.get('cnpj') or request.filial_ativa.cnpj,
            ambiente=ambiente,
            defaults={'uf': request.POST.get('uf') or request.filial_ativa.uf, 'ativo': True},
        )
        config.uf = request.POST.get('uf') or request.filial_ativa.uf
        config.ultimo_nsu = request.POST.get('ultimo_nsu', '').strip()
        certificado = request.FILES.get('certificado_digital')
        if certificado:
            nome = certificado.name or ''
            if not nome.lower().endswith(('.pfx', '.p12')):
                messages.error(request, 'Use um certificado A1 nos formatos .pfx ou .p12.')
                return render(request, self.template_name, self.get_context(config))
            senha = getattr(settings, 'FISCAL_DFE_CERT_PASSWORD', '')
            if senha:
                conteudo = certificado.read()
                certificado.seek(0)
                try:
                    info = validar_certificado_a1_para_config(
                        conteudo,
                        senha,
                        cnpj_esperado=config.cnpj,
                    )
                except DomainError as exc:
                    messages.error(request, str(exc))
                    return render(request, self.template_name, self.get_context(config))
                config.certificado_thumbprint = info.thumbprint
                config.certificado_cnpj = info.cnpj
                config.certificado_titular = info.subject[:255]
                config.certificado_emissor = info.issuer[:255]
                config.certificado_validade_inicio = info.not_before
                config.certificado_validade_fim = info.not_after
            else:
                config.certificado_thumbprint = ''
                config.certificado_cnpj = ''
                config.certificado_titular = ''
                config.certificado_emissor = ''
                config.certificado_validade_inicio = None
                config.certificado_validade_fim = None
                messages.warning(
                    request,
                    'Certificado anexado sem validar conteudo: senha deve ficar apenas em FISCAL_DFE_CERT_PASSWORD.',
                )
            config.certificado_digital = certificado
            config.certificado_nome = nome
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
            messages.success(request, 'Ciencia local registrada no ERP. Nenhum evento foi enviado a SEFAZ.')
        elif acao == 'desconhecer':
            ManifestoFiscalService.marcar_desconhecida(documento)
            messages.success(request, 'Operacao marcada localmente como desconhecida. Nenhum evento foi enviado a SEFAZ.')
        elif acao == 'nao-realizada':
            ManifestoFiscalService.marcar_nao_realizada(documento)
            messages.success(request, 'Operacao marcada localmente como nao realizada. Nenhum evento foi enviado a SEFAZ.')
        else:
            messages.error(request, 'Acao invalida.')
        return redirect('fiscal:manifesto-list')


class ManifestoFiscalImportarEntradaView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'

    def post(self, request, pk):
        documento = get_object_or_404(
            ManifestoFiscalDocumento.objects.for_filial(request.filial_ativa),
            pk=pk,
        )
        try:
            resultado = ManifestoFiscalService.importar_entrada(documento, request.user)
        except DomainError as exc:
            messages.error(request, str(exc))
            return redirect('fiscal:manifesto-list')

        if resultado.criada:
            messages.success(
                request,
                f'Manifesto importado. NF {resultado.entrada.numero_nf} pronta para conferencia.',
            )
        else:
            messages.info(request, f'Manifesto vinculado a NF {resultado.entrada.numero_nf} ja existente.')
        return redirect('compras:entrada-conferencia', pk=resultado.entrada.pk)


class ManifestoFiscalAnexarXMLView(PermissaoRequiredMixin, View):
    permissao_modulo = 'compras'
    permissao_acao = 'criar'
    template_name = 'fiscal/manifesto/anexar_xml.html'

    def get_documento(self, request, pk):
        return get_object_or_404(
            ManifestoFiscalDocumento.objects.for_filial(request.filial_ativa),
            pk=pk,
        )

    def get(self, request, pk):
        documento = self.get_documento(request, pk)
        return render(request, self.template_name, {'documento': documento})

    def post(self, request, pk):
        documento = self.get_documento(request, pk)
        nome_arquivo = ''
        xml_texto = request.POST.get('xml_texto', '')
        arquivo = request.FILES.get('arquivo_xml')
        if arquivo:
            nome_arquivo = arquivo.name
            raw = arquivo.read()
            try:
                xml_texto = raw.decode('utf-8')
            except UnicodeDecodeError:
                xml_texto = raw.decode('latin1')

        try:
            ManifestoFiscalService.anexar_xml_completo(
                documento,
                xml_texto=xml_texto,
                nome_arquivo=nome_arquivo,
            )
        except DomainError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, {
                'documento': documento,
                'xml_texto': request.POST.get('xml_texto', ''),
            })

        if request.POST.get('acao') == 'salvar_importar':
            try:
                resultado = ManifestoFiscalService.importar_entrada(documento, request.user)
            except DomainError as exc:
                messages.error(request, str(exc))
                return redirect('fiscal:manifesto-list')
            messages.success(
                request,
                f'XML anexado e NF {resultado.entrada.numero_nf} pronta para conferencia.',
            )
            return redirect('compras:entrada-conferencia', pk=resultado.entrada.pk)

        messages.success(request, 'XML completo anexado ao Manifesto.')
        return redirect('fiscal:manifesto-list')
