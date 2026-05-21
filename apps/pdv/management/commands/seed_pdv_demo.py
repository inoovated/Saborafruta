"""Popula dados de exemplo para testar o PDV: formas de pagamento e produtos."""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Filial
from apps.financeiro.models import FormaPagamento
from apps.produtos.models import Produto, ProdutoFilial, UnidadeMedida


FORMAS = [
    ("Dinheiro", "dinheiro"),
    ("PIX", "pix"),
    ("Cartão de Crédito", "cartao_credito"),
    ("Cartão de Débito", "cartao_debito"),
    ("Transferência", "ted"),
    ("Boleto", "boleto"),
]

PRODUTOS = [
    ("Polpa de Acerola 1kg", "7891000000017", "KG", "12.90"),
    ("Polpa de Caju 1kg", "7891000000024", "KG", "11.50"),
    ("Polpa de Manga 1kg", "7891000000031", "KG", "13.90"),
    ("Polpa de Goiaba 1kg", "7891000000048", "KG", "12.50"),
    ("Polpa de Maracujá 1kg", "7891000000055", "KG", "15.90"),
    ("Polpa de Cajá 1kg", "7891000000062", "KG", "14.50"),
    ("Polpa de Graviola 1kg", "7891000000079", "KG", "16.90"),
    ("Polpa de Abacaxi 1kg", "7891000000086", "KG", "11.90"),
    ("Suco Concentrado Laranja 500ml", "7891000000093", "UN", "9.90"),
    ("Açaí Tradicional 1kg", "7891000000109", "UN", "22.90"),
]


class Command(BaseCommand):
    help = "Cria formas de pagamento e produtos de exemplo para o PDV."

    @transaction.atomic
    def handle(self, *args, **options):
        filiais = list(Filial.objects.all())
        if not filiais:
            self.stdout.write(self.style.ERROR("Nenhuma filial encontrada."))
            return

        empresas = {f.empresa_id for f in filiais}
        formas_criadas = 0
        for empresa_id in empresas:
            for descricao, tipo in FORMAS:
                _, criado = FormaPagamento.objects.get_or_create(
                    empresa_id=empresa_id, descricao=descricao,
                    defaults={"tipo": tipo, "ativo": True},
                )
                formas_criadas += int(criado)
        self.stdout.write(self.style.SUCCESS(f"Formas de pagamento: +{formas_criadas}"))

        unidades = {u.sigla: u for u in UnidadeMedida.objects.all()}
        produtos_criados = 0
        for filial in filiais:
            for idx, (descricao, ean, um_sigla, preco) in enumerate(PRODUTOS, start=1):
                um = unidades.get(um_sigla) or unidades.get("UN")
                if um is None:
                    self.stdout.write(self.style.ERROR("Sem UnidadeMedida cadastrada."))
                    return
                codigo = f"PDV{idx:03d}"
                produto, criado = Produto.objects.get_or_create(
                    filial=filial, codigo=codigo,
                    defaults={
                        "descricao": descricao,
                        "descricao_pdv": descricao,
                        "codigo_barras": ean,
                        "ncm": "20089900",
                        "unidade_medida": um,
                        "preco_venda": Decimal(preco),
                        "ativo": True,
                    },
                )
                produtos_criados += int(criado)
                ProdutoFilial.objects.get_or_create(
                    produto=produto, filial=filial,
                    defaults={"ativo": True},
                )
        self.stdout.write(self.style.SUCCESS(f"Produtos: +{produtos_criados}"))
        self.stdout.write(self.style.SUCCESS("Seed do PDV concluído."))
