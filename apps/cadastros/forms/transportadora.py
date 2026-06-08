from django import forms

from apps.cadastros.models import Motorista, Representante, Transportadora


class TransportadoraForm(forms.ModelForm):
    class Meta:
        model = Transportadora
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cnpj': forms.TextInput(attrs={'maxlength': '14'}),
            'cep': forms.TextInput(attrs={'maxlength': '8'}),
        }


class MotoristaForm(forms.ModelForm):
    class Meta:
        model = Motorista
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cpf': forms.TextInput(attrs={'maxlength': '14', 'placeholder': '000.000.000-00'}),
            'validade_cnh': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial is not None:
            self.fields['transportadora'].queryset = Transportadora.objects.for_filial(filial).filter(ativo=True)
        self.fields['transportadora'].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input w-full')


class RepresentanteForm(forms.ModelForm):
    class Meta:
        model = Representante
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cpf': forms.TextInput(attrs={'maxlength': '11'}),
        }
