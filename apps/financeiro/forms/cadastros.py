from django import forms

from apps.financeiro.models import CentroCusto, PlanoContas


class CentroCustoForm(forms.ModelForm):
    class Meta:
        model = CentroCusto
        fields = ["codigo", "nome", "descricao", "ativo"]
        labels = {
            "codigo": "Código",
            "nome": "Nome",
            "descricao": "Descrição",
            "ativo": "Ativo",
        }
        widgets = {
            "descricao": forms.TextInput(),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        qs = CentroCusto.objects.filter(empresa=self.empresa, codigo__iexact=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if self.empresa and qs.exists():
            raise forms.ValidationError("Já existe centro de custo com este código.")
        return codigo


class PlanoContasDespesaForm(forms.ModelForm):
    class Meta:
        model = PlanoContas
        fields = ["conta_pai", "codigo", "descricao", "aceita_lancamento", "ativo"]
        labels = {
            "conta_pai": "Conta pai",
            "codigo": "Código",
            "descricao": "Descrição",
            "aceita_lancamento": "Aceita lançamento",
            "ativo": "Ativo",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        qs = PlanoContas.objects.none()
        if empresa:
            qs = PlanoContas.objects.filter(empresa=empresa, tipo="D", ativo=True).order_by("codigo")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk).exclude(conta_pai=self.instance)
        self.fields["conta_pai"].queryset = qs
        self.fields["conta_pai"].required = False
        self.fields["conta_pai"].empty_label = "Sem conta pai, criar categoria"

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        qs = PlanoContas.objects.filter(empresa=self.empresa, codigo__iexact=codigo, tipo="D")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if self.empresa and qs.exists():
            raise forms.ValidationError("Já existe despesa com este código.")
        return codigo

    def clean(self):
        cleaned = super().clean()
        conta_pai = cleaned.get("conta_pai")
        if conta_pai and conta_pai.nivel >= 3:
            raise forms.ValidationError("Tipo de despesa é o terceiro nível. Escolha uma categoria ou subcategoria como pai.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.empresa = self.empresa
        instance.tipo = "D"
        instance.nivel = (instance.conta_pai.nivel + 1) if instance.conta_pai_id else 1
        if commit:
            instance.save()
            self.save_m2m()
        return instance
