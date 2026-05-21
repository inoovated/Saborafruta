"""Formulários da tela de Parâmetros do Sistema."""
from django import forms

from apps.core.constants.choices import UF
from apps.core.models import Filial
from apps.core.models.parametros import ParametrosSistema

def _aplicar_estilo(form):
    """Aplica a classe de input padrão aos widgets (exceto checkbox/file).

    A classe ``param-input`` é estilizada no template parametros_form.html,
    com suporte a tema claro e escuro.
    """
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.ClearableFileInput)):
            continue
        css = widget.attrs.get('class', '')
        widget.attrs['class'] = (css + ' param-input').strip()


class FilialIdentidadeForm(forms.ModelForm):
    """Identificação e endereço da filial — editados pela tela de Parâmetros."""

    class Meta:
        model = Filial
        fields = [
            'nome_fantasia', 'razao_social', 'cnpj',
            'inscricao_estadual', 'inscricao_municipal', 'email',
            'cep', 'endereco', 'numero', 'bairro', 'cidade',
            'codigo_municipio_ibge', 'uf', 'telefone',
        ]
        widgets = {
            'uf': forms.Select(choices=[('', '—')] + list(UF.choices)),
            'cnpj': forms.TextInput(attrs={'placeholder': '00000000000000', 'maxlength': '14'}),
            'cep': forms.TextInput(attrs={'placeholder': '00000000', 'maxlength': '8'}),
            'codigo_municipio_ibge': forms.TextInput(attrs={'placeholder': '0000000', 'maxlength': '7'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)

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


class ParametrosSistemaForm(forms.ModelForm):
    """Logo e e-mail secundário."""

    class Meta:
        model = ParametrosSistema
        fields = ['logo', 'email_secundario']
        widgets = {
            'email_secundario': forms.EmailInput(attrs={'placeholder': 'contato@empresa.com.br'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)
