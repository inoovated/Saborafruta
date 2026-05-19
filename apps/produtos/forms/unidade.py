from django import forms

from apps.produtos.models import UnidadeMedida


class UnidadeMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadeMedida
        fields = ['sigla', 'descricao', 'tipo', 'fator_conversao_base', 'ativo']
