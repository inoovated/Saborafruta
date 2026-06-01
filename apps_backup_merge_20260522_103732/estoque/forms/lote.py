from django import forms

from apps.cadastros.models import Fornecedor
from apps.estoque.models import LoteProduto
from apps.produtos.models import Produto


class LoteProdutoForm(forms.ModelForm):
    class Meta:
        model = LoteProduto
        exclude = [
            'filial', 'quantidade_atual', 'ordem_producao_id',
            'created_at', 'updated_at',
        ]
        widgets = {
            'data_fabricacao': forms.DateInput(attrs={'type': 'date'}),
            'data_validade': forms.DateInput(attrs={'type': 'date'}),
            'quantidade_inicial': forms.NumberInput(attrs={
                'step': '0.001',
                'inputmode': 'decimal',
                'data-decimal-places': '3',
                'data-fractional-stock': '1',
            }),
            'custo_unitario': forms.NumberInput(attrs={
                'step': '0.0001',
                'inputmode': 'decimal',
                'data-decimal-places': '4',
            }),
            'motivo_bloqueio': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['produto'].queryset = Produto.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('descricao')
            self.fields['fornecedor'].queryset = Fornecedor.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('razao_social')
        if self.instance and self.instance.pk:
            self.fields['quantidade_inicial'].disabled = True
            self.fields['quantidade_inicial'].help_text = (
                'Quantidade inicial nao pode ser alterada depois da criacao. '
                'Use uma movimentacao ou ajuste de estoque.'
            )
