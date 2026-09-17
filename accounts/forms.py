from uuid import uuid4

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import EmailVerification
from .verification import normalize_email_address, users_for_email


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label='メールアドレス',
        max_length=254,
        help_text='アカウントを有効にするための確認メールをお送りします。',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ('email',)

    def clean_email(self):
        email = normalize_email_address(self.cleaned_data['email'])
        if users_for_email(email).exists():
            raise forms.ValidationError(
                'このメールアドレスでは登録できません。ログインまたは確認メールの再送をご利用ください。',
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f'user_{uuid4().hex}'
        user.is_active = False
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(label='メールアドレス', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'username', 'autofocus': True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('username')
        self.order_fields(['email', 'password'])

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email and password:
            email = normalize_email_address(email)
            self.cleaned_data['email'] = email
            candidates = list(users_for_email(email)[:2])
            user = candidates[0] if len(candidates) == 1 else None
            # Keep Django's password hashing work on unknown/ambiguous identities too.
            self.user_cache = authenticate(self.request,
                username=user.username if user else f'unknown_{uuid4().hex}', password=password)
            if user is None or self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def get_invalid_login_error(self):
        return forms.ValidationError(
            'メールアドレスまたはパスワードを確認してください。', code='invalid_login',
        )

    def confirm_login_allowed(self, user):
        if not user.is_active or EmailVerification.objects.filter(
                user=user, verified_at__isnull=True).exists():
            raise self.get_invalid_login_error()


class ResendVerificationForm(forms.Form):
    email = forms.EmailField(label='メールアドレス', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}))

    def clean_email(self):
        return normalize_email_address(self.cleaned_data['email'])
