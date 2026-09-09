from django import forms
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label='メールアドレス',
        help_text='パスワードを忘れたときの再設定に使用します。',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')
