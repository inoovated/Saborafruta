from django import forms
from django.forms import inlineformset_factory

from apps.producao.models import FichaTecnica, ItemFichaTecnica


class FichaTecnicaForm(forms.ModelForm):
    class Meta:
        model = FichaTecnica
        exclude = ['filial', 'created_at', 'updated_at']
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }


ItemFichaTecnicaFormSet = inlineformset_factory(
    FichaTecnica,
    ItemFichaTecnica,
    fields=['materia_prima', 'quantidade', 'perda_prevista', 'observacao'],
    extra=1,
    can_delete=True,
)
