"""Formulários para o módulo Outras Movimentações."""
from django import forms

from apps.cadastros.models import Cliente, Fornecedor
from apps.estoque.models import LoteProduto
from apps.produtos.models import Produto

QUANTIDADE_WIDGET = forms.NumberInput(attrs={
    'step': '0.001',
    'inputmode': 'decimal',
    'data-decimal-places': '3',
    'data-fractional-stock': '1',
})

VALOR_WIDGET = forms.NumberInput(attrs={
    'step': '0.01',
    'inputmode': 'decimal',
    'data-decimal-places': '2',
})


class DevolucaoClienteForm(forms.Form):
    """Formulário de devolução de mercadoria pelo cliente."""

    CFOP_CHOICES = [
        ('1201', '1201 – Devolução de venda de produto fabricado no próprio estado'),
        ('1202', '1202 – Devolução de venda de mercadoria adquirida de terceiros'),
    ]

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        label='Cliente',
        help_text='Selecione o cliente que está efetuando a devolução.',
    )
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        label='Produto',
    )
    lote = forms.ModelChoiceField(
        queryset=LoteProduto.objects.none(),
        required=False,
        label='Lote',
        help_text='Obrigatório quando o produto controla lote.',
    )
    quantidade = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        label='Quantidade devolvida',
        widget=QUANTIDADE_WIDGET,
    )
    valor_unitario = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        label='Valor unitário (R$)',
        help_text='Valor unitário da devolução para cálculo do crédito ao cliente.',
        widget=VALOR_WIDGET,
    )
    cfop = forms.ChoiceField(
        choices=CFOP_CHOICES,
        label='CFOP',
    )
    documento_numero = forms.CharField(
        max_length=30,
        required=False,
        label='NF de devolução',
        help_text='Número da nota fiscal de devolução (opcional).',
    )
    gerar_credito = forms.BooleanField(
        initial=True,
        required=False,
        label='Gerar crédito para o cliente',
        help_text='Quando marcado, um crédito financeiro será registrado para o cliente.',
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='Observação',
        help_text='Obrigatória — descreva o motivo da devolução.',
    )

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['cliente'].queryset = Cliente.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('razao_social')
            self.fields['produto'].queryset = Produto.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('descricao')
            self.fields['lote'].queryset = LoteProduto.objects.for_filial(filial).select_related(
                'produto',
            ).order_by('produto__descricao', 'data_validade')

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        lote = cleaned_data.get('lote')
        if produto and produto.controla_lote and not lote:
            self.add_error('lote', 'Informe o lote para produto com controle de lote.')
        if produto and lote and lote.produto_id != produto.pk:
            self.add_error('lote', 'O lote informado não pertence ao produto selecionado.')
        gerar_credito = cleaned_data.get('gerar_credito')
        valor_unitario = cleaned_data.get('valor_unitario')
        if gerar_credito and not valor_unitario:
            self.add_error(
                'valor_unitario',
                'Informe o valor unitário para gerar crédito ao cliente.',
            )
        return cleaned_data


class DevolucaoFornecedorForm(forms.Form):
    """Formulário de devolução de mercadoria ao fornecedor."""

    CFOP_CHOICES = [
        ('5201', '5201 - Devolução de compra para industrialização'),
        ('5202', '5202 - Devolução de compra para comercialização'),
        ('5205', '5205 - Devolução de compra de ativo imobilizado'),
        ('5411', '5411 - Devolução de compra com substituição tributária'),
        ('6201', '6201 - Devolução de compra para industrialização (outro estado)'),
        ('6202', '6202 - Devolução de compra para comercialização (outro estado)'),
    ]

    fornecedor = forms.ModelChoiceField(
        queryset=Fornecedor.objects.none(),
        label='Fornecedor',
        help_text='Fornecedor para o qual a mercadoria será devolvida.',
    )
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        label='Produto',
    )
    lote = forms.ModelChoiceField(
        queryset=LoteProduto.objects.none(),
        required=False,
        label='Lote',
        help_text='Obrigatório quando o produto controla lote.',
    )
    quantidade = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        label='Quantidade devolvida',
        widget=QUANTIDADE_WIDGET,
    )
    valor_unitario = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        label='Valor unitário (R$)',
        help_text='Valor unitário da mercadoria para fins fiscais.',
        widget=VALOR_WIDGET,
    )
    cfop = forms.ChoiceField(
        choices=CFOP_CHOICES,
        initial='5202',
        label='CFOP',
    )
    nota_fiscal_origem = forms.CharField(
        max_length=30,
        required=False,
        label='NF de origem',
        help_text='Número da nota fiscal de compra original (opcional).',
    )
    documento_numero = forms.CharField(
        max_length=30,
        required=False,
        label='NF de devolução',
        help_text='Número da nota fiscal de devolução (opcional).',
    )
    motivo = forms.ChoiceField(
        choices=[
            ('qualidade', 'Problema de qualidade'),
            ('divergencia', 'Divergência de quantidade/especificação'),
            ('avaria', 'Avaria / dano no transporte'),
            ('prazo', 'Produto fora do prazo'),
            ('erro_pedido', 'Erro no pedido'),
            ('outro', 'Outro motivo'),
        ],
        label='Motivo da devolução',
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='Observação',
        help_text='Obrigatória: descreva detalhes da devolução.',
    )

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['fornecedor'].queryset = Fornecedor.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('razao_social')
            self.fields['produto'].queryset = Produto.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('descricao')
            self.fields['lote'].queryset = LoteProduto.objects.for_filial(filial).filter(
                status=LoteProduto.Status.ATIVO,
            ).select_related('produto').order_by('produto__descricao', 'data_validade')

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        lote = cleaned_data.get('lote')
        if produto and produto.controla_lote and not lote:
            self.add_error('lote', 'Informe o lote para produto com controle de lote.')
        if produto and lote and lote.produto_id != produto.pk:
            self.add_error('lote', 'O lote informado não pertence ao produto selecionado.')
        return cleaned_data


class SaidaEspecialForm(forms.Form):
    """Formulário unificado para Venda Bonificada, Roubo/Furto, Perda e Deterioração."""

    TIPO_CHOICES = [
        ('bonificacao', 'Venda Bonificada (CFOP 5910)'),
        ('roubo', 'Roubo / Furto (CFOP 5927)'),
        ('perda', 'Perda (CFOP 5927)'),
        ('deterioracao', 'Deterioração / Perecimento (CFOP 5928)'),
    ]

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        label='Tipo de saída',
    )
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        label='Produto',
    )
    lote = forms.ModelChoiceField(
        queryset=LoteProduto.objects.none(),
        required=False,
        label='Lote',
        help_text='Obrigatório quando o produto controla lote.',
    )
    quantidade = forms.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=0.001,
        label='Quantidade',
        widget=QUANTIDADE_WIDGET,
    )
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=False,
        label='Cliente (Venda Bonificada)',
        help_text='Preenchimento obrigatório apenas para Venda Bonificada.',
    )
    documento_numero = forms.CharField(
        max_length=30,
        required=False,
        label='Número do documento',
        help_text='Número de NF ou outro documento de referência (opcional).',
    )
    observacao = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='Observação',
        help_text='Obrigatória — descreva o motivo da saída.',
    )

    def __init__(self, *args, filial=None, **kwargs):
        super().__init__(*args, **kwargs)
        if filial:
            self.fields['produto'].queryset = Produto.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('descricao')
            self.fields['lote'].queryset = LoteProduto.objects.for_filial(filial).filter(
                status=LoteProduto.Status.ATIVO,
            ).select_related('produto').order_by('produto__descricao', 'data_validade')
            self.fields['cliente'].queryset = Cliente.objects.for_filial(filial).filter(
                ativo=True,
            ).order_by('razao_social')

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        lote = cleaned_data.get('lote')
        tipo = cleaned_data.get('tipo')
        if produto and produto.controla_lote and not lote:
            self.add_error('lote', 'Informe o lote para produto com controle de lote.')
        if produto and lote and lote.produto_id != produto.pk:
            self.add_error('lote', 'O lote informado não pertence ao produto selecionado.')
        if tipo == 'bonificacao' and not cleaned_data.get('cliente'):
            self.add_error('cliente', 'Informe o cliente para Venda Bonificada.')
        return cleaned_data
