from django import forms

from apps.produtos.models import MarcaProduto


class MarcaProdutoForm(forms.ModelForm):
    class Meta:
        model = MarcaProduto
        fields = ['nome', 'descricao', 'ativo']
        labels = {
            'nome': 'Nome da marca / fabricante',
            'descricao': 'Descricao',
            'ativo': 'Ativa',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-4 h-4 rounded accent-blue-500'
            else:
                existing = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing} form-input'.strip()
