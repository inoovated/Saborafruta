from django import forms
from django.forms import inlineformset_factory

from apps.core.models import PerfilAcesso, Permissao, Usuario


class UsuarioForm(forms.ModelForm):
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password'},
            render_value=False,
        ),
        required=False,
        help_text='Deixe em branco para manter a senha atual.',
    )
    senha_confirmacao = forms.CharField(
        label='Confirme a senha',
        widget=forms.PasswordInput(
            attrs={'autocomplete': 'new-password'},
            render_value=False,
        ),
        required=False,
    )

    class Meta:
        model = Usuario
        fields = [
            'empresa', 'filial', 'perfil', 'nome', 'cpf', 'email', 'telefone',
            'comissao_percentual', 'pin_code', 'pin_exige_supervisor', 'ativo',
        ]

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get('senha')
        confirmacao = cleaned.get('senha_confirmacao')

        if not self.instance.pk and not senha:
            raise forms.ValidationError('Senha obrigatoria para novo usuario.')

        if self.instance.pk and senha and not confirmacao:
            cleaned['senha'] = ''
            cleaned['senha_confirmacao'] = ''
            senha = ''

        if senha and senha != confirmacao:
            raise forms.ValidationError('As senhas nao coincidem.')

        return cleaned

    def save(self, commit=True):
        usuario = super().save(commit=False)
        senha = self.cleaned_data.get('senha')
        if senha:
            usuario.set_password(senha)
        if commit:
            usuario.save()
        return usuario


class PerfilAcessoForm(forms.ModelForm):
    class Meta:
        model = PerfilAcesso
        fields = ['empresa', 'nome', 'descricao', 'is_admin', 'ativo']


PermissaoFormSet = inlineformset_factory(
    PerfilAcesso,
    Permissao,
    fields=[
        'modulo', 'pode_ver', 'pode_criar', 'pode_editar', 'pode_excluir',
        'pode_cancelar', 'pode_aprovar', 'pode_exportar',
    ],
    extra=1,
    can_delete=True,
)
