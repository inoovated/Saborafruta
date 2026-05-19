from django import forms

from apps.estoque.models import Inventario, ItemInventario


class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['descricao', 'bloquear_movimentacoes', 'observacao']
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }


class ItemInventarioForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ['quantidade_contada', 'justificativa']
        widgets = {
            'justificativa': forms.Textarea(attrs={'rows': 2}),
        }
