from django import forms

from apps.produtos.models import CategoriaProduto
from apps.qualidade.models import ParametroQualidadeCategoria, ParametroQualidadeProduto


class DecimalBRField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip()
            if "," in value:
                value = value.replace(".", "").replace(",", ".")
        return super().to_python(value)


class ParametroQualidadeBaseForm(forms.ModelForm):
    valor_minimo = DecimalBRField(
        label="Minimo",
        required=False,
        max_digits=10,
        decimal_places=3,
        widget=forms.TextInput(attrs={"placeholder": "0,000"}),
    )
    valor_ideal = DecimalBRField(
        label="Ideal",
        required=False,
        max_digits=10,
        decimal_places=3,
        widget=forms.TextInput(attrs={"placeholder": "0,000"}),
    )
    valor_maximo = DecimalBRField(
        label="Maximo",
        required=False,
        max_digits=10,
        decimal_places=3,
        widget=forms.TextInput(attrs={"placeholder": "0,000"}),
    )
    opcoes_texto = forms.CharField(
        label="Opcoes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Use uma opcao por linha ou separe por virgula.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.opcoes:
            self.fields["opcoes_texto"].initial = "\n".join(str(item) for item in self.instance.opcoes)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "quality-checkbox"})
            else:
                field.widget.attrs.update({"class": "quality-input"})

    def clean_nome_parametro(self):
        return (self.cleaned_data.get("nome_parametro") or "").strip()

    def clean_unidade_medida(self):
        return (self.cleaned_data.get("unidade_medida") or "").strip()

    def clean_valor_texto_ideal(self):
        return (self.cleaned_data.get("valor_texto_ideal") or "").strip()

    def clean(self):
        cleaned = super().clean()
        tipo_valor = cleaned.get("tipo_valor")
        minimo = cleaned.get("valor_minimo")
        maximo = cleaned.get("valor_maximo")
        if tipo_valor == "numero" and minimo is not None and maximo is not None and minimo > maximo:
            raise forms.ValidationError("O valor minimo nao pode ser maior que o valor maximo.")
        if tipo_valor in ("texto", "sim_nao", "selecao"):
            cleaned["valor_minimo"] = None
            cleaned["valor_ideal"] = None
            cleaned["valor_maximo"] = None
        if tipo_valor == "numero":
            cleaned["valor_texto_ideal"] = ""
            cleaned["opcoes"] = []
        return cleaned

    def save(self, commit=True):
        parametro = super().save(commit=False)
        texto = self.cleaned_data.get("opcoes_texto") or ""
        partes = []
        for linha in texto.replace(",", "\n").splitlines():
            valor = linha.strip()
            if valor:
                partes.append(valor)
        parametro.opcoes = partes if parametro.tipo_valor == "selecao" else []
        if commit:
            parametro.save()
            self.save_m2m()
        return parametro


class ParametroQualidadeProdutoForm(ParametroQualidadeBaseForm):
    class Meta:
        model = ParametroQualidadeProduto
        fields = [
            "etapa",
            "nome_parametro",
            "tipo_valor",
            "unidade_medida",
            "valor_minimo",
            "valor_ideal",
            "valor_maximo",
            "valor_texto_ideal",
            "opcoes_texto",
            "obrigatorio",
            "ativo",
        ]
        labels = {
            "etapa": "Etapa",
            "nome_parametro": "Parametro",
            "tipo_valor": "Tipo",
            "unidade_medida": "Unidade",
            "valor_minimo": "Minimo",
            "valor_ideal": "Ideal",
            "valor_maximo": "Maximo",
            "valor_texto_ideal": "Valor esperado",
            "obrigatorio": "Obrigatorio",
            "ativo": "Ativo",
        }
        widgets = {
            "nome_parametro": forms.TextInput(attrs={"placeholder": "Ex.: Brix, pH, temperatura, cor"}),
            "unidade_medida": forms.TextInput(attrs={"placeholder": "Ex.: Brix, pH, C, %, g"}),
            "valor_texto_ideal": forms.TextInput(attrs={"placeholder": "Ex.: amarelo claro, sem impurezas"}),
        }


class ParametroQualidadeCategoriaForm(ParametroQualidadeBaseForm):
    categoria_base = forms.ModelChoiceField(
        label="Categoria",
        queryset=CategoriaProduto.objects.none(),
        required=True,
        empty_label="---------",
        widget=forms.Select(),
    )
    subcategoria = forms.ModelChoiceField(
        label="Subcategoria",
        queryset=CategoriaProduto.objects.none(),
        required=False,
        empty_label="---------",
        widget=forms.Select(),
    )

    class Meta(ParametroQualidadeProdutoForm.Meta):
        model = ParametroQualidadeCategoria
        fields = ["categoria_base", "subcategoria"] + ParametroQualidadeProdutoForm.Meta.fields
        labels = {
            **ParametroQualidadeProdutoForm.Meta.labels,
            "categoria_base": "Categoria",
            "subcategoria": "Subcategoria",
        }
        widgets = {
            **ParametroQualidadeProdutoForm.Meta.widgets,
        }

    def __init__(self, *args, categorias=None, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = categorias if categorias is not None else self.fields["categoria_base"].queryset
        categorias_base = categorias.filter(categoria_pai__isnull=True)
        subcategorias = categorias.filter(categoria_pai__isnull=False)
        self.fields["categoria_base"].queryset = categorias_base
        self.fields["subcategoria"].queryset = subcategorias
        if self.instance and self.instance.pk and self.instance.categoria_id:
            categoria = self.instance.categoria
            if categoria.categoria_pai_id:
                self.fields["categoria_base"].initial = categoria.categoria_pai_id
                self.fields["subcategoria"].initial = categoria.pk
            else:
                self.fields["categoria_base"].initial = categoria.pk
        self.fields["categoria_base"].widget.attrs.update({"class": "quality-input", "data-quality-category": "base"})
        self.fields["subcategoria"].widget.attrs.update({"class": "quality-input", "data-quality-category": "sub"})

    def clean(self):
        cleaned = super().clean()
        categoria_base = cleaned.get("categoria_base")
        subcategoria = cleaned.get("subcategoria")
        if subcategoria and categoria_base and subcategoria.categoria_pai_id != categoria_base.pk:
            self.add_error("subcategoria", "Subcategoria nao pertence a categoria selecionada.")
        return cleaned

    def save(self, commit=True):
        parametro = super().save(commit=False)
        parametro.categoria = self.cleaned_data.get("subcategoria") or self.cleaned_data.get("categoria_base")
        if commit:
            parametro.save()
            self.save_m2m()
        return parametro
