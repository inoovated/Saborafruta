from django import forms
from django.db.models import Q

from apps.produtos.models import CategoriaProduto


class CategoriaProdutoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProduto
        fields = ['categoria_pai', 'nome', 'descricao', 'ativo']
        labels = {
            'categoria_pai': 'Categoria pai',
            'nome': 'Nome',
            'descricao': 'Descricao',
            'ativo': 'Ativa',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, empresa=None, filial=None, modo=None, **kwargs):
        self.modo = modo or 'categoria'
        super().__init__(*args, **kwargs)
        if empresa:
            qs = CategoriaProduto.objects.filter(
                empresa=empresa, ativo=True, categoria_pai__isnull=True,
            )
            if filial:
                qs = CategoriaProduto.objects.for_filial(filial).filter(
                    empresa=empresa, ativo=True, categoria_pai__isnull=True,
                )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
                if self.instance.categoria_pai_id:
                    # Usar Q para evitar TypeError ao combinar queryset com
                    # distinct (for_filial) com outro queryset via operador |
                    qs = CategoriaProduto.objects.filter(
                        Q(pk__in=qs.values('pk')) | Q(pk=self.instance.categoria_pai_id)
                    )
            self.fields['categoria_pai'].queryset = qs
        self.fields['categoria_pai'].required = False
        self.fields['categoria_pai'].label = 'Categoria'
        self.fields['categoria_pai'].help_text = 'Categoria onde a subcategoria ficara atrelada.'
        if modo == 'categoria':
            self.fields.pop('categoria_pai', None)
            self.fields['nome'].label = 'Nome da Categoria'
        elif modo == 'subcategoria':
            self.fields['categoria_pai'].required = True
            self.fields['nome'].label = 'Nome da Subcategoria'
            self.fields['categoria_pai'].help_text = 'Escolha a categoria principal onde esta subcategoria ficara atrelada.'
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-4 h-4 rounded accent-blue-500'
            else:
                existing = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f'{existing} form-input'.strip()

    def clean(self):
        cleaned = super().clean()
        if self.modo == 'subcategoria' and not cleaned.get('categoria_pai'):
            self.add_error('categoria_pai', 'Escolha uma categoria para esta subcategoria.')
        return cleaned
