from django import forms

from apps.producao.models import FichaTecnica


class CriarOrdemProducaoForm(forms.Form):
    ficha_tecnica = forms.ModelChoiceField(queryset=FichaTecnica.objects.none(), label='Ficha Técnica')
    quantidade_planejada = forms.DecimalField(
        max_digits=12, decimal_places=3, min_value=0.001,
        label='Quantidade a produzir',
    )
    data_inicio_prevista = forms.DateTimeField(
        required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label='Início previsto',
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), required=False,
    )

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['ficha_tecnica'].queryset = FichaTecnica.objects.filter(
                filial=filial, status=FichaTecnica.Status.ATIVA,
            ).select_related('produto_acabado')


class EncerrarOrdemProducaoForm(forms.Form):
    quantidade_produzida = forms.DecimalField(
        max_digits=12, decimal_places=3, min_value=0.001,
        label='Quantidade realmente produzida',
    )
    peso_saida = forms.DecimalField(
        max_digits=12, decimal_places=3, required=False,
        label='Peso de saída (kg)',
        help_text='Opcional. Usado para cálculo de rendimento por peso.',
    )
    numero_lote_gerado = forms.CharField(
        max_length=60, required=False, label='Número do lote',
        help_text='Se vazio, o sistema gera automaticamente (ex: L20260417-0000001)',
    )
    data_validade = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data de validade do lote',
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), required=False,
    )


class CancelarOrdemProducaoForm(forms.Form):
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Motivo do cancelamento',
    )
