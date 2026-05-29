"""Formulários de Plano de Contas."""
from django import forms

from apps.financeiro.models.conta_bancaria import PlanoContas


class PlanoContasForm(forms.ModelForm):
    """Criação / edição de uma conta no plano de contas."""

    class Meta:
        model = PlanoContas
        fields = [
            "conta_pai",
            "codigo",
            "descricao",
            "tipo",
            "nivel",
            "aceita_lancamento",
            "ativo",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"placeholder": "ex.: 1.1.01"}),
            "descricao": forms.TextInput(attrs={"placeholder": "ex.: Vendas de mercadorias"}),
            "nivel": forms.NumberInput(attrs={"min": "1", "max": "9"}),
        }
        labels = {
            "conta_pai": "Conta pai",
            "codigo": "Código",
            "descricao": "Descrição",
            "tipo": "Tipo",
            "nivel": "Nível hierárquico",
            "aceita_lancamento": "Aceita lançamentos",
            "ativo": "Ativo",
        }
        help_texts = {
            "conta_pai": "Deixe em branco para contas de primeiro nível.",
            "nivel": "1 = raiz, 2 = grupo, 3 = subgrupo, 4+ = analítico.",
            "aceita_lancamento": "Marque apenas em contas analíticas (último nível).",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields["conta_pai"].queryset = (
                PlanoContas.objects
                .filter(empresa=empresa)
                .order_by("codigo")
            )
        else:
            self.fields["conta_pai"].queryset = PlanoContas.objects.none()
        self.fields["conta_pai"].required = False
