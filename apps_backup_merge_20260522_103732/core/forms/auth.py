from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'placeholder': 'seu@email.com',
            'autofocus': 'autofocus',
            'autocomplete': 'email',
        }),
    )
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        }),
    )
    lembrar = forms.BooleanField(label='Lembrar neste dispositivo', required=False)
