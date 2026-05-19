"""Indicadores de rendimento por linha de produção."""
from decimal import Decimal
from django.db.models import Sum, Avg, F
from apps.producao.models import OrdemProducao, PerdaProducao
from apps.producao.constants.enums import StatusOP


class RendimentoService:

    METAS_POR_PREFIXO = {"PF": 75, "MA": 85, "EB": 92}

    @staticmethod
    def rendimento_medio(linha_producao, filial, dias=30):
        from django.utils import timezone
        from datetime import timedelta
        ate = timezone.now()
        de = ate - timedelta(days=dias)
        qs = OrdemProducao.objects.filter(
            linha_producao=linha_producao, filial=filial,
            status=StatusOP.ENCERRADA,
            data_encerramento__range=(de, ate),
        )
        agg = qs.aggregate(
            total_planejado=Sum("quantidade_planejada"),
            total_produzido=Sum("quantidade_produzida"),
            total_perdido=Sum("quantidade_perdida"),
            media_rendimento=Avg("rendimento_percentual"),
        )
        meta = RendimentoService.METAS_POR_PREFIXO.get(
            linha_producao.prefixo_lote,
            float(linha_producao.meta_rendimento_percentual or 0),
        )
        media = float(agg["media_rendimento"] or 0)
        return {
            "linha": linha_producao.nome,
            "media_rendimento_percentual": round(media, 2),
            "meta_percentual": meta,
            "atinge_meta": media >= meta,
            "ops_consideradas": qs.count(),
            **agg,
        }

    @staticmethod
    def perdas_por_categoria(linha_producao, filial, dias=30):
        from django.utils import timezone
        from datetime import timedelta
        ate = timezone.now()
        de = ate - timedelta(days=dias)
        return list(
            PerdaProducao.objects
            .filter(
                ordem_producao__linha_producao=linha_producao,
                ordem_producao__filial=filial,
                created_at__range=(de, ate),
            )
            .values("tipo_perda")
            .annotate(
                total_quantidade=Sum("quantidade"),
                total_custo=Sum("impacto_custo"),
            )
            .order_by("-total_quantidade")
        )
