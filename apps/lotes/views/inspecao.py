"""CRUD de inspeções de lote."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.core.services.permissions import PermissaoRequiredMixin
from apps.estoque.models import LoteProduto
from apps.lotes.models import InspecaoLote


class LoteInspecaoListView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    template_name = 'lotes/inspecao_list.html'

    def get(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa).select_related('produto'), pk=pk)
        inspecoes = (
            InspecaoLote.objects
            .filter(lote=lote)
            .select_related('responsavel')
            .order_by('-data_inspecao')
        )
        return render(request, self.template_name, {
            'lote': lote,
            'inspecoes': inspecoes,
        })


class LoteInspecaoCreateView(PermissaoRequiredMixin, View):
    permissao_modulo = 'estoque'
    permissao_acao = 'criar'
    template_name = 'lotes/inspecao_form.html'

    def get(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa).select_related('produto'), pk=pk)
        return render(request, self.template_name, {
            'lote': lote,
            'resultado_choices': InspecaoLote.Resultado.choices,
            'data_inspecao_default': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        })

    def post(self, request, pk):
        lote = get_object_or_404(LoteProduto.objects.for_filial(request.filial_ativa).select_related('produto'), pk=pk)
        resultado = request.POST.get('resultado', '').strip()
        parecer = request.POST.get('parecer', '').strip()
        observacao = request.POST.get('observacao', '').strip()
        data_inspecao_str = request.POST.get('data_inspecao', '').strip()

        if not resultado or resultado not in dict(InspecaoLote.Resultado.choices):
            messages.error(request, 'Selecione um resultado válido.')
            return render(request, self.template_name, {
                'lote': lote,
                'resultado_choices': InspecaoLote.Resultado.choices,
                'data_inspecao_default': data_inspecao_str or timezone.now().strftime('%Y-%m-%dT%H:%M'),
            })

        try:
            from django.utils.dateparse import parse_datetime
            data_inspecao = parse_datetime(data_inspecao_str) if data_inspecao_str else timezone.now()
            if data_inspecao is None:
                data_inspecao = timezone.now()
        except Exception:
            data_inspecao = timezone.now()

        inspecao = InspecaoLote.objects.create(
            lote=lote,
            responsavel=request.user,
            data_inspecao=data_inspecao,
            resultado=resultado,
            parecer=parecer,
            observacao=observacao,
        )

        # Se reprovado, coloca lote em quarentena automaticamente
        if resultado == InspecaoLote.Resultado.REPROVADO:
            lote.status = LoteProduto.Status.QUARENTENA
            lote.motivo_bloqueio = f'Reprovado em inspeção #{inspecao.pk}: {parecer}'
            lote.save(update_fields=['status', 'motivo_bloqueio'])
            messages.warning(request, f'Lote "{lote.numero_lote}" movido para quarentena após reprovação na inspeção.')
        elif resultado == InspecaoLote.Resultado.QUARENTENA:
            lote.status = LoteProduto.Status.QUARENTENA
            lote.motivo_bloqueio = f'Quarentena por inspeção #{inspecao.pk}: {parecer}'
            lote.save(update_fields=['status', 'motivo_bloqueio'])
            messages.warning(request, f'Lote "{lote.numero_lote}" em quarentena.')
        else:
            messages.success(request, f'Inspeção registrada: {inspecao.get_resultado_display()}.')

        return redirect(reverse('lotes:inspecao-list', kwargs={'pk': lote.pk}))
