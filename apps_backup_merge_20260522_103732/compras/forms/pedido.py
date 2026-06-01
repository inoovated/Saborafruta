from django import forms

from apps.cadastros.models import Fornecedor
from apps.compras.models import PedidoCompra
from apps.produtos.models import Produto


class PedidoCompraForm(forms.ModelForm):
    class Meta:
        model = PedidoCompra
        fields = [
            'fornecedor', 'data_entrega_prevista',
            'modalidade_frete', 'valor_frete', 'valor_outras_despesas',
            'observacao',
        ]
        widgets = {
            'data_entrega_prevista': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['fornecedor'].queryset = Fornecedor.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('razao_social')


class AdicionarItemCompraForm(forms.Form):
    produto = forms.ModelChoiceField(queryset=Produto.objects.none(), label='Produto')
    quantidade = forms.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    valor_unitario = forms.DecimalField(max_digits=14, decimal_places=4, min_value=0)
    valor_ipi = forms.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, initial=0, required=False,
        label='IPI (R$)',
    )

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['produto'].queryset = Produto.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('descricao')


class CancelarPedidoCompraForm(forms.Form):
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Motivo')
