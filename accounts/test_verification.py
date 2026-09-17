from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail, signing
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import EmailVerification
from .verification import TOKEN_SALT, send_verification_email, verification_token


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   SITE_URL='https://quiz.example.com', EMAIL_VERIFICATION_TIMEOUT=86400,
                   EMAIL_VERIFICATION_RESEND_INTERVAL=60)
class EmailVerificationTests(TestCase):
    password = 'Study-Pharmacy-482!'

    def create_user(self, email='student@example.com', active=False, verified=False, tracked=True):
        user = get_user_model().objects.create_user(
            username=f'internal_{get_user_model().objects.count()}', email=email,
            password=self.password, is_active=active,
        )
        # Simulate legacy/imported values without UserManager's normalization.
        get_user_model().objects.filter(pk=user.pk).update(email=email)
        user.email = email
        if tracked:
            EmailVerification.objects.create(user=user, verified_at=timezone.now() if verified else None)
        return user

    def signup(self, email='new@example.com', **kwargs):
        return self.client.post(reverse('signup'), {
            'email': email, 'password1': self.password, 'password2': self.password,
        }, **kwargs)

    def login(self, email, password=None):
        return self.client.post(reverse('login'), {
            'email': email, 'password': self.password if password is None else password,
        })

    def verify(self, user):
        return self.client.get(reverse('verify_email', args=[verification_token(user)]))

    def test_signup_normalizes_and_generates_unique_internal_names(self):
        response = self.signup(' New@Example.COM ')
        self.assertRedirects(response, reverse('verification_sent'))
        user = get_user_model().objects.get()
        self.assertEqual(user.email, 'new@example.com')
        self.assertRegex(user.username, r'^user_[0-9a-f]{32}$')
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_active)
        self.assertIsNone(user.email_verification.verified_at)
        self.assertIsNotNone(user.email_verification.last_sent_at)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])
        self.assertIn('https://quiz.example.com/accounts/verify-email/', mail.outbox[0].body)
        self.assertNotIn(user.username, mail.outbox[0].body)
        self.signup('another@example.com')
        self.assertEqual(len(set(get_user_model().objects.values_list('username', flat=True))), 2)

    def test_signup_requires_email_and_hides_username(self):
        self.assertNotContains(self.client.get(reverse('signup')), 'name="username"')
        response = self.signup('')
        self.assertIn('email', response.context['form'].errors)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_duplicate_email_variants_are_rejected_without_changing_legacy_data(self):
        user = self.create_user(email=' Test@Example.COM ', active=True, tracked=False)
        for email in ['test@example.com', 'TEST@example.com', ' Test@example.com ']:
            with self.subTest(email=email):
                response = self.signup(email)
                self.assertIn('email', response.context['form'].errors)
        user.refresh_from_db()
        self.assertEqual(user.email, ' Test@Example.COM ')
        self.assertTrue(user.is_active)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_verification_enables_login_without_automatic_login(self):
        self.signup()
        user = get_user_model().objects.get()
        self.login(user.email)
        self.assertNotIn('_auth_user_id', self.client.session)
        url = next(line for line in mail.outbox[0].body.splitlines() if line.startswith('https://'))
        response = self.client.get(url)
        self.assertContains(response, '確認が完了しました')
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertIn('no-store', response['Cache-Control'])
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.email_verification.verified_at)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.login(user.email), '/')

    def test_invalid_tampered_expired_missing_and_changed_email_tokens(self):
        user = self.create_user()
        token = verification_token(user)
        invalid_tokens = [
            'invalid', token + 'tampered',
            signing.dumps({'user_id': 999999, 'email': user.email}, salt=TOKEN_SALT),
            signing.dumps({'user_id': 'bad', 'email': user.email}, salt=TOKEN_SALT),
            signing.dumps({'user_id': 10 ** 100, 'email': user.email}, salt=TOKEN_SALT),
            signing.dumps([], salt=TOKEN_SALT),
        ]
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() - 86401):
            invalid_tokens.append(verification_token(user))
        user.email = 'changed@example.com'
        user.save(update_fields=['email'])
        invalid_tokens.append(token)
        for invalid in invalid_tokens:
            with self.subTest(token_kind=invalid[:12]):
                response = self.client.get(reverse('verify_email', args=[invalid]))
                self.assertContains(response, '無効または期限切れ')
                self.assertContains(response, reverse('resend_verification'))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNone(user.email_verification.verified_at)

    def test_verification_timeout_setting_is_used(self):
        user = self.create_user()
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() - 120):
            token = verification_token(user)
        with self.settings(EMAIL_VERIFICATION_TIMEOUT=60):
            self.assertContains(self.client.get(reverse('verify_email', args=[token])), '無効または期限切れ')

    def test_confirmed_link_is_idempotent_and_cannot_restore_suspended_account(self):
        user = self.create_user()
        self.verify(user)
        first_verified_at = EmailVerification.objects.get(user=user).verified_at
        self.assertContains(self.verify(user), '既に確認済み')
        self.assertEqual(EmailVerification.objects.get(user=user).verified_at, first_verified_at)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertContains(self.verify(user), '既に確認済み')
        self.client.post(reverse('resend_verification'), {'email': user.email})
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 0)

    def test_untracked_or_ambiguous_account_cannot_be_activated(self):
        user = self.create_user(tracked=False)
        self.assertContains(self.verify(user), '無効または期限切れ')
        EmailVerification.objects.create(user=user)
        self.create_user(email=' STUDENT@example.com ', tracked=False)
        self.assertContains(self.verify(user), '無効または期限切れ')
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_existing_active_user_can_login_with_normalized_email(self):
        user = self.create_user(email=' Student@Example.COM ', active=True, tracked=False)
        for email in ['student@example.com', 'STUDENT@example.com', ' Student@example.com ']:
            with self.subTest(email=email):
                self.assertRedirects(self.login(email), '/')
                self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
                self.client.logout()
        self.assertFalse(EmailVerification.objects.exists())

    def test_failed_login_messages_do_not_disclose_account_state(self):
        active = self.create_user(email='active@example.com', active=True, tracked=False)
        inactive = self.create_user(email='inactive@example.com', tracked=False)
        pending = self.create_user(email='pending@example.com')
        # Even an accidentally activated pending user must finish verification.
        pending.is_active = True
        pending.save(update_fields=['is_active'])
        self.create_user(email='duplicate@example.com', active=True, tracked=False)
        self.create_user(email=' DUPLICATE@example.com ', active=True, tracked=False)
        errors = []
        for email, password in [
            (active.email, 'wrong'), (inactive.email, self.password), (pending.email, self.password),
            ('unknown@example.com', self.password), ('duplicate@example.com', self.password),
        ]:
            response = self.login(email, password)
            errors.append(str(response.context['form'].non_field_errors()))
            self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(set(errors)), 1)

    def test_admin_keeps_username_login(self):
        user = get_user_model().objects.create_superuser(username='admin-editor', password=self.password)
        response = self.client.post(reverse('admin:login'), {
            'username': user.username, 'password': self.password, 'next': reverse('admin:index'),
        })
        self.assertRedirects(response, reverse('admin:index'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_resend_normalizes_and_respects_cooldown(self):
        user = self.create_user()
        url = reverse('resend_verification')
        self.assertRedirects(self.client.post(url, {'email': ' STUDENT@example.com '}), reverse('verification_sent'))
        self.assertEqual(len(mail.outbox), 1)
        self.client.post(url, {'email': user.email})
        self.assertEqual(len(mail.outbox), 1)
        EmailVerification.objects.filter(user=user).update(last_sent_at=timezone.now() - timedelta(seconds=61))
        self.client.post(url, {'email': user.email})
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_responses_identical_for_all_account_states_and_failures(self):
        pending = self.create_user(email='pending@example.com')
        self.create_user(email='verified@example.com', active=True, verified=True)
        self.create_user(email='suspended@example.com', verified=True)
        self.create_user(email='legacy@example.com', tracked=False)
        self.create_user(email='duplicate@example.com')
        self.create_user(email='DUPLICATE@example.com')
        pages = []
        for email in ['missing@example.com', 'verified@example.com', 'suspended@example.com',
                      'legacy@example.com', 'duplicate@example.com', pending.email, pending.email]:
            response = self.client.post(reverse('resend_verification'), {'email': email}, follow=True)
            self.assertRedirects(response, reverse('verification_sent'))
            pages.append(response.content)
        self.assertEqual(len(set(pages)), 1)
        self.assertEqual(len(mail.outbox), 1)
        EmailVerification.objects.filter(user=pending).update(last_sent_at=None)
        with patch('accounts.verification.send_mail', side_effect=RuntimeError('secret')):
            with self.assertLogs('accounts.verification', level='ERROR'):
                response = self.client.post(reverse('resend_verification'), {'email': pending.email}, follow=True)
        self.assertEqual(response.content, pages[0])

    def test_delivery_failure_keeps_pending_account_and_redacts_logs(self):
        with patch('accounts.verification.send_mail', side_effect=RuntimeError('API_KEY_SECRET')):
            with self.assertLogs('accounts.verification', level='ERROR') as logs:
                response = self.signup()
        self.assertContains(response, '確認メールを送信できませんでした')
        self.assertContains(response, reverse('resend_verification'))
        self.assertNotContains(response, 'API_KEY_SECRET')
        self.assertNotIn('API_KEY_SECRET', '\n'.join(logs.output))
        user = get_user_model().objects.get()
        self.assertFalse(user.is_active)
        self.assertIsNone(user.email_verification.verified_at)
        with patch('accounts.verification.send_mail') as send:
            send_verification_email(user)
        send.assert_not_called()

    def test_backend_returning_zero_is_a_delivery_failure(self):
        user = self.create_user()
        with patch('accounts.verification.send_mail', return_value=0):
            with self.assertLogs('accounts.verification', level='ERROR'):
                self.assertFalse(send_verification_email(user))

    @override_settings(ALLOWED_HOSTS=['testserver', 'untrusted.example.com'])
    def test_mail_uses_configured_origin_not_request_host(self):
        self.signup(HTTP_HOST='untrusted.example.com')
        self.assertIn(settings.SITE_URL, mail.outbox[0].body)
        self.assertNotIn('untrusted.example.com', mail.outbox[0].body)

    def test_password_reset_skips_pending_users_and_omits_internal_username(self):
        user = self.create_user()
        self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertEqual(len(mail.outbox), 0)
        self.verify(user)
        self.client.post(reverse('password_reset'), {'email': user.email})
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(user.username, mail.outbox[0].body)

    def test_password_toggles_cover_login_signup_and_password_reset(self):
        user = self.create_user(active=True, verified=True)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset = reverse('password_reset_confirm', args=[uid, token])
        for url, fields in [(reverse('login'), ['password']),
                            (reverse('signup'), ['password1', 'password2']),
                            (reset, ['new_password1', 'new_password2'])]:
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'js/auth.js')
            for field in fields:
                self.assertContains(response, f'name="{field}"')
                self.assertContains(response, f'data-password-toggle="id_{field}"')
                self.assertContains(response, f'aria-controls="id_{field}"')
            self.assertContains(response, 'class="auth-password-toggle" type="button"', count=len(fields))
            self.assertContains(response, 'aria-pressed="false" hidden', count=len(fields))

    def test_internal_username_not_in_user_pages_including_empty_email(self):
        for email in ['', 'student@example.com']:
            user = self.create_user(email=email, active=True, tracked=False)
            self.client.force_login(user)
            for url in ['/', reverse('mypage')]:
                self.assertNotContains(self.client.get(url), user.username)
            self.client.logout()

    def test_csrf_required_for_registration_resend_and_login(self):
        client = Client(enforce_csrf_checks=True)
        for name in ['signup', 'resend_verification', 'login']:
            self.assertEqual(client.post(reverse(name), {'email': 'new@example.com'}).status_code, 403)

    def test_authenticated_signup_redirects_to_mypage(self):
        self.client.force_login(self.create_user(active=True, verified=True))
        self.assertRedirects(self.client.get(reverse('signup')), reverse('mypage'))
