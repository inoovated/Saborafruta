from django import forms

from apps.produtos.models import ItemTabelaPreco, TabelaPreco


class TabelaPrecoForm(forms.ModelForm):
    class Meta:
        model = TabelaPreco
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
        }


class ItemTabelaPrecoForm(forms.ModelForm):
    class Meta:
        model = ItemTabelaPreco
        fields = ['produto', 'preco_unitario', 'desconto_maximo', 'quantidade_minima']
