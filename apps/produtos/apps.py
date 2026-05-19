from django.apps import AppConfig


class ProdutosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.produtos'
    verbose_name = 'Produtos'

    def ready(self):
        from apps.core.signals import register_for_audit
        from .models import (
            BrindeProduto,
            BrindeProdutoItem,
            KitCategoria,
            KitCategoriaRegra,
            KitProduto,
            KitProdutoItem,
            Produto,
            ProdutoFilial,
            PromocaoQuantidade,
            PromocaoQuantidadeFaixa,
        )
        register_for_audit(Produto, 'produtos')
        register_for_audit(ProdutoFilial, 'produtos')
        register_for_audit(PromocaoQuantidade, 'produtos')
        register_for_audit(PromocaoQuantidadeFaixa, 'produtos')
        register_for_audit(KitProduto, 'produtos')
        register_for_audit(KitProdutoItem, 'produtos')
        register_for_audit(BrindeProduto, 'produtos')
        register_for_audit(BrindeProdutoItem, 'produtos')
        register_for_audit(KitCategoria, 'produtos')
        register_for_audit(KitCategoriaRegra, 'produtos')
