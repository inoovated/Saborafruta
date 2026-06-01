from django import forms

from apps.cadastros.models import Representante, Transportadora


class TransportadoraForm(forms.ModelForm):
    class Meta:
        model = Transportadora
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cnpj': forms.TextInput(attrs={'maxlength': '14'}),
            'cep': forms.TextInput(attrs={'maxlength': '8'}),
        }


class RepresentanteForm(forms.ModelForm):
    class Meta:
        model = Representante
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cpf': forms.TextInput(attrs={'maxlength': '11'}),
        }
