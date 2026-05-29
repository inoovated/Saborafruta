"""Views do módulo Outras Movimentações de Estoque."""
from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.core.services.exceptions import DomainError
from apps.core.services.permissions import PERMISSION_DENIED_MESSAGE, PermissaoRequiredMixin
from apps.estoque.forms.outras_movimentacoes import (
    DevolucaoClienteForm,
    DevolucaoFornecedorForm,
    SaidaEspecialForm,
)
from apps.estoque.models import MovimentacaoEstoque
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.views.permissoes import permissoes_estoque

# CFOP fixos por tipo de operação
CFOP_MAP = {
    'bonificacao': '5910',
    'roubo': '5927',
    'perda': '5927',
    'deterioracao': '5928',
}

TIPOS_OUTRAS = {
    MovimentacaoEstoque.TipoOperacao.DEVOLUCAO_CLIENTE,
    MovimentacaoEstoque.TipoOperacao.DEVOLUCAO_FORNECEDOR,
    MovimentacaoEstoque.TipoOperacao.BONIFICACAO,
    MovimentacaoEstoque.TipoOperacao.ROUBO,
    MovimentacaoEstoque.TipoOperacao.PERDA,
    MovimentacaoEstoque.TipoOperacao.DETERIORACAO,
}


class OutrasMovimentacoesHubView(PermissaoRequiredMixin, View):
    """Hub com os 5 cards de operação e histórico recente."""

    permissao_modulo = 'estoque'
    permissao_acao = 'ver'

    def get(self, request):
        filial = request.filial_ativa
        perms = permissoes_estoque(request)

        historico = (
            MovimentacaoEstoque.objects
            .filter(filial=filial, tipo_operacao__in=TIPOS_OUTRAS)
            .select_related('produto', 'usuario', 'lote')
            .order_by('-data_movimentacao')[:20]
        )

        return render(request, 'estoque/outras_movimentacoes/hub.html', {
            'title': 'Outras Movimentações',
            'historico': historico,
            **perms,
        })


class DevolucaoClienteView(PermissaoRequiredMixin, View):
    """Devolução de mercadoria pelo cliente: gera ajuste positivo de estoque e crédito."""

    permissao_modulo = 'estoque'
    permissao_acao = 'criar'

    def _get_filial(self, request):
        return request.filial_ativa

    def get(self, request):
        filial = self._get_filial(request)
        form = DevolucaoClienteForm(filial=filial)
        perms = permissoes_estoque(request)
        return render(request, 'estoque/outras_movimentacoes/devolucao.html', {
            'title': 'Devolução de Cliente',
            'form': form,
            'cancel_url': reverse('estoque:outras-mov-hub'),
            **perms,
        })

    @transaction.atomic
    def post(self, request):
        filial = self._get_filial(request)
        form = DevolucaoClienteForm(request.POST, filial=filial)

        if not form.is_valid():
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/devolucao.html', {
                'title': 'Devolução de Cliente',
                'form': form,
                'cancel_url': reverse('estoque:outras-mov-hub'),
                **perms,
            })

        data = form.cleaned_data
        try:
            mov = MovimentacaoService.registrar_movimentacao(
                produto_id=data['produto'].pk,
                filial_id=filial.pk,
                tipo_operacao=MovimentacaoEstoque.TipoOperacao.DEVOLUCAO_CLIENTE,
                quantidade=data['quantidade'],
                usuario_id=request.user.pk,
                lote_id=data['lote'].pk if data.get('lote') else None,
                valor_unitario=data.get('valor_unitario'),
                documento_tipo=MovimentacaoEstoque.DocumentoTipo.OUTRAS,
                documento_numero=data.get('documento_numero', ''),
                observacao=data['observacao'],
            )

            if data.get('gerar_credito') and data.get('valor_unitario'):
                from apps.financeiro.models.credito_cliente import CreditoCliente
                valor_total = data['valor_unitario'] * data['quantidade']
                CreditoCliente.objects.create(
                    filial=filial,
                    cliente=data['cliente'],
                    valor=valor_total,
                    valor_utilizado=Decimal('0'),
                    motivo='devolucao',
                    documento_numero=data.get('documento_numero', ''),
                    cfop=data['cfop'],
                    observacao=data['observacao'],
                    usuario=request.user,
                    status=CreditoCliente.Status.DISPONIVEL,
                )
                messages.success(
                    request,
                    f'Devolução registrada com sucesso (mov. #{mov.pk}). '
                    f'Crédito de R$ {valor_total:.2f} gerado para {data["cliente"]}.',
                )
            else:
                messages.success(
                    request,
                    f'Devolução de cliente registrada com sucesso (mov. #{mov.pk}).',
                )

        except DomainError as exc:
            messages.error(request, str(exc))
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/devolucao.html', {
                'title': 'Devolução de Cliente',
                'form': form,
                'cancel_url': reverse('estoque:outras-mov-hub'),
                **perms,
            })

        return redirect(reverse('estoque:outras-mov-hub'))


class DevolucaoFornecedorView(PermissaoRequiredMixin, View):
    """Devolução de mercadoria ao fornecedor: gera saída de estoque com CFOP 52xx/62xx."""

    permissao_modulo = 'estoque'
    permissao_acao = 'criar'

    def _get_filial(self, request):
        return request.filial_ativa

    def get(self, request):
        filial = self._get_filial(request)
        form = DevolucaoFornecedorForm(filial=filial)
        perms = permissoes_estoque(request)
        return render(request, 'estoque/outras_movimentacoes/devolucao_fornecedor.html', {
            'title': 'Devolução ao Fornecedor',
            'form': form,
            'cancel_url': reverse('estoque:outras-mov-hub'),
            **perms,
        })

    @transaction.atomic
    def post(self, request):
        filial = self._get_filial(request)
        form = DevolucaoFornecedorForm(request.POST, filial=filial)

        if not form.is_valid():
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/devolucao_fornecedor.html', {
                'title': 'Devolução ao Fornecedor',
                'form': form,
                'cancel_url': reverse('estoque:outras-mov-hub'),
                **perms,
            })

        data = form.cleaned_data
        motivo_label = dict(form.fields['motivo'].choices).get(data['motivo'], data['motivo'])
        observacao = f"[{motivo_label}] {data['observacao']}"
        if data.get('nota_fiscal_origem'):
            observacao = f"NF origem: {data['nota_fiscal_origem']} | {observacao}"
        if data.get('valor_unitario') is not None:
            observacao = f"Valor unitário: R$ {data['valor_unitario']:.2f} | {observacao}"

        try:
            movs = MovimentacaoService.registrar_saida_fefo(
                produto_id=data['produto'].pk,
                filial_id=filial.pk,
                quantidade=data['quantidade'],
                usuario_id=request.user.pk,
                tipo_operacao=MovimentacaoEstoque.TipoOperacao.DEVOLUCAO_FORNECEDOR,
                documento_tipo=MovimentacaoEstoque.DocumentoTipo.OUTRAS,
                documento_numero=data.get('documento_numero', ''),
                observacao=observacao,
            )

            messages.success(
                request,
                f'Devolução ao fornecedor registrada com sucesso. '
                f'CFOP {data["cfop"]}: {len(movs)} lote(s) movimentado(s).',
            )

        except DomainError as exc:
            messages.error(request, str(exc))
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/devolucao_fornecedor.html', {
                'title': 'Devolução ao Fornecedor',
                'form': form,
                'cancel_url': reverse('estoque:outras-mov-hub'),
                **perms,
            })

        return redirect(reverse('estoque:outras-mov-hub'))


class SaidaEspecialView(PermissaoRequiredMixin, View):
    """Saída especial: Bonificação, Roubo/Furto, Perda ou Deterioração."""

    permissao_modulo = 'estoque'
    permissao_acao = 'criar'

    def _get_filial(self, request):
        return request.filial_ativa

    def get(self, request):
        filial = self._get_filial(request)
        form = SaidaEspecialForm(filial=filial)
        perms = permissoes_estoque(request)
        return render(request, 'estoque/outras_movimentacoes/saida_especial.html', {
            'title': 'Saída Especial',
            'form': form,
            'cfop_map': CFOP_MAP,
            **perms,
        })

    @transaction.atomic
    def post(self, request):
        filial = self._get_filial(request)
        form = SaidaEspecialForm(request.POST, filial=filial)

        if not form.is_valid():
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/saida_especial.html', {
                'title': 'Saída Especial',
                'form': form,
                'cfop_map': CFOP_MAP,
                **perms,
            })

        data = form.cleaned_data
        tipo = data['tipo']

        tipo_operacao_map = {
            'bonificacao': MovimentacaoEstoque.TipoOperacao.BONIFICACAO,
            'roubo': MovimentacaoEstoque.TipoOperacao.ROUBO,
            'perda': MovimentacaoEstoque.TipoOperacao.PERDA,
            'deterioracao': MovimentacaoEstoque.TipoOperacao.DETERIORACAO,
        }
        tipo_operacao = tipo_operacao_map[tipo]
        cfop = CFOP_MAP[tipo]

        observacao = data['observacao']
        if data.get('documento_numero'):
            observacao = f"Doc.: {data['documento_numero']} — {observacao}"

        try:
            movs = MovimentacaoService.registrar_saida_fefo(
                produto_id=data['produto'].pk,
                filial_id=filial.pk,
                quantidade=data['quantidade'],
                usuario_id=request.user.pk,
                tipo_operacao=tipo_operacao,
                documento_tipo=MovimentacaoEstoque.DocumentoTipo.OUTRAS,
                documento_numero=data.get('documento_numero', ''),
                observacao=observacao,
            )

            tipo_label = dict(SaidaEspecialForm.TIPO_CHOICES).get(tipo, tipo)
            messages.success(
                request,
                f'{tipo_label} registrada com sucesso. '
                f'CFOP {cfop} — {len(movs)} lote(s) movimentado(s).',
            )

        except DomainError as exc:
            messages.error(request, str(exc))
            perms = permissoes_estoque(request)
            return render(request, 'estoque/outras_movimentacoes/saida_especial.html', {
                'title': 'Saída Especial',
                'form': form,
                'cfop_map': CFOP_MAP,
                **perms,
            })

        return redirect(reverse('estoque:outras-mov-hub'))
