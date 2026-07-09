from django.core.management.base import BaseCommand
from apps.pdv.models import VendaPDV, ItemVendaPDV, PagamentoVendaPDV, MovimentacaoCaixa, SessaoPDV, Caixa


class Command(BaseCommand):
    help = 'Remove todas as vendas do PDV (apenas para ambiente de testes)'

    def handle(self, *args, **options):
        total = VendaPDV.objects.count()
        PagamentoVendaPDV.objects.all().delete()
        ItemVendaPDV.objects.all().delete()
        MovimentacaoCaixa.objects.all().delete()
        SessaoPDV.objects.all().delete()
        VendaPDV.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'{total} vendas removidas com sucesso.'))
