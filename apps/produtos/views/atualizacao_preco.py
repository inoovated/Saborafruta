"""Rotina de atualizacao de preco de venda em massa."""
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.cadastros.models import Fornecedor
from apps.compras.models import EntradaNF
from apps.core.services.permissions import PermissaoRequiredMixin
from apps.produtos.models import CategoriaProduto, MarcaProduto
from apps.produtos.services.atualizacao_preco_service import AtualizacaoPrecoService


class AtualizacaoPrecoView(PermissaoRequiredMixin, View):
    permissao_modulo = 'produtos'
    permissao_acao = 'editar'
    template_name = 'produtos/atualizacao_preco/index.html'

    def _entrada(self, request):
        entrada_id = request.GET.get('entrada_id')
        origem = request.GET.get('origem')
        if origem != 'xml' or not entrada_id:
            return None
        return get_object_or_404(
            EntradaNF.objects.for_filial(request.filial_ativa).select_related('fornecedor'),
            pk=entrada_id,
        )

    def _linhas(self, request, entrada):
        if entrada:
            return AtualizacaoPrecoService.linhas_xml(entrada)
        filtros = {
            'q': request.GET.get('q', ''),
            'categoria': request.GET.get('categoria', ''),
            'marca': request.GET.get('marca', ''),
            'fornecedor': request.GET.get('fornecedor', ''),
            'com_estoque': request.GET.get('quick') == 'com_estoque',
            'margem_baixa': request.GET.get('quick') == 'margem_baixa',
        }
        return AtualizacaoPrecoService.linhas_avulsas(request.filial_ativa, filtros)

    def _regra(self, request):
        return {
            'tipo': request.GET.get('regra_tipo') or request.POST.get('regra_tipo') or 'percentual',
            'valor': request.GET.get('valor') or request.POST.get('valor') or '10',
            'direcao': request.GET.get('direcao') or request.POST.get('direcao') or 'aumentar',
            'arredondamento': request.GET.get('arredondamento') or request.POST.get('arredondamento') or 'centavos',
        }

    def get(self, request):
        entrada = self._entrada(request)
        etapa = request.GET.get('etapa') or 'selecao'
        if etapa not in {'selecao', 'regras', 'simulacao', 'aplicacao'}:
            etapa = 'selecao'
        linhas = self._linhas(request, entrada)
        regra = self._regra(request)
        cenarios = AtualizacaoPrecoService.cenarios(linhas)
        maior_ganho = max((cenario['ganho_bruto'] for cenario in cenarios), default=Decimal('1')) or Decimal('1')
        for cenario in cenarios:
            cenario['bar_width'] = int((cenario['ganho_bruto'] / maior_ganho) * Decimal('100')) if maior_ganho else 0
        cenario_escolhido = next((cenario for cenario in cenarios if cenario.get('recomendado')), cenarios[0] if cenarios else None)
        context = self._contexto_base(request, entrada, etapa, linhas, regra)
        context.update({
            'cenarios': cenarios,
            'cenario_escolhido': cenario_escolhido,
            'simulacao_regra': AtualizacaoPrecoService.simular_cenario(linhas, regra),
        })
        return render(request, self.template_name, context)

    def post(self, request):
        entrada = self._entrada(request)
        linhas = self._linhas(request, entrada)
        regra = self._regra(request)
        if request.POST.get('acao') != 'aplicar':
            return redirect(self._url_etapa(request, 'simulacao', entrada))
        if not linhas:
            messages.warning(request, 'Nenhum produto selecionado para atualizar.')
            return redirect(self._url_etapa(request, 'selecao', entrada))
        lote = AtualizacaoPrecoService.aplicar_atualizacao(
            request=request,
            entrada=entrada,
            linhas=linhas,
            regra=regra,
        )
        aplicados = lote.itens.filter(status='aplicado').count()
        bloqueados = lote.itens.filter(status='bloqueado').count()
        messages.success(request, f'Atualização aplicada em {aplicados} produto(s). {bloqueados} produto(s) ficaram bloqueados.')
        return redirect(self._url_etapa(request, 'aplicacao', entrada) + f'&lote_id={lote.pk}')

    def _url_etapa(self, request, etapa, entrada):
        base = reverse('produtos:atualizacao-precos')
        origem = 'xml' if entrada else 'avulsa'
        params = [f'origem={origem}', f'etapa={etapa}']
        if entrada:
            params.append(f'entrada_id={entrada.pk}')
        return f'{base}?{"&".join(params)}'

    def _contexto_base(self, request, entrada, etapa, linhas, regra):
        resumo = AtualizacaoPrecoService.resumo(linhas)
        origem_label = (
            f'Itens da XML NF-e {entrada.numero_nf}'
            if entrada
            else 'Uso avulso'
        )
        return {
            'entrada': entrada,
            'origem': 'xml' if entrada else 'avulsa',
            'origem_label': origem_label,
            'etapa': etapa,
            'linhas': linhas,
            'resumo': resumo,
            'regra': regra,
            'categorias': CategoriaProduto.objects.for_filial(request.filial_ativa).filter(ativo=True, categoria_pai__isnull=True).order_by('nome'),
            'marcas': MarcaProduto.objects.for_filial(request.filial_ativa).filter(ativo=True).order_by('nome'),
            'fornecedores': Fornecedor.objects.for_filial(request.filial_ativa).filter(ativo=True).order_by('razao_social', 'nome_fantasia'),
            'urls': {
                'selecao': self._url_etapa(request, 'selecao', entrada),
                'regras': self._url_etapa(request, 'regras', entrada),
                'simulacao': self._url_etapa(request, 'simulacao', entrada),
                'aplicacao': self._url_etapa(request, 'aplicacao', entrada),
                'continuar_entrada': (
                    reverse('compras:entrada-conferencia', args=[entrada.pk])
                    if entrada
                    else reverse('produtos:produto-list')
                ),
            },
        }
