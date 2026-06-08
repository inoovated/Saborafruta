"""Formulários de Praça e Rota."""
from django import forms

from apps.cadastros.models import Praca, Rota


class PracaForm(forms.ModelForm):
    class Meta:
        model = Praca
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'cidades': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'São Paulo, Guarulhos, Osasco, Barueri...',
            }),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input w-full')


class RotaForm(forms.ModelForm):
    class Meta:
        model = Rota
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'pracas': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial is not None:
            self.fields['pracas'].queryset = Praca.objects.for_filial(filial).filter(ativo=True).order_by('nome')
        else:
            self.fields['pracas'].queryset = Praca.objects.none()
        self.fields['pracas'].required = False
        # Apply form-input class to all except the M2M checkbox field
        for name, field in self.fields.items():
            if name != 'pracas':
                field.widget.attrs.setdefault('class', 'form-input w-full')
