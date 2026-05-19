from django import forms

from apps.core.constants.choices import UF
from apps.core.models import Empresa, Filial


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        exclude = ['created_at', 'updated_at', 'certificado_senha_hash']
        widgets = {
            'uf': forms.Select(choices=[('', '—')] + list(UF.choices)),
            'cnpj': forms.TextInput(attrs={'placeholder': '00000000000000', 'maxlength': '14'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000000', 'maxlength': '8'}),
        }

    def clean_cnpj(self):
        cnpj = ''.join(filter(str.isdigit, self.cleaned_data.get('cnpj', '')))
        if len(cnpj) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        return cnpj

    def clean_cep(self):
        cep = ''.join(filter(str.isdigit, self.cleaned_data.get('cep', '')))
        if cep and len(cep) != 8:
            raise forms.ValidationError('CEP deve conter 8 dígitos.')
        return cep


class FilialForm(forms.ModelForm):
    class Meta:
        model = Filial
        exclude = ['created_at', 'updated_at', 'certificado_senha_hash']
        widgets = {
            'uf': forms.Select(choices=UF.choices),
            'cnpj': forms.TextInput(attrs={'placeholder': '00000000000000', 'maxlength': '14'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000000', 'maxlength': '8'}),
        }

    def clean_cnpj(self):
        cnpj = ''.join(filter(str.isdigit, self.cleaned_data.get('cnpj', '')))
        if len(cnpj) != 14:
            raise forms.ValidationError('CNPJ deve conter 14 dígitos.')
        return cnpj
