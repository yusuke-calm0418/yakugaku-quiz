from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = 'Study-Pharmacy-482!'
        self.user = get_user_model().objects.create_user(
            username='student', email='student@example.com', password=self.password,
        )

    def test_signup_saves_email_and_shows_confirmation(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newstudent', 'email': 'new@example.com',
            'password1': self.password, 'password2': self.password,
        }, follow=True)
        self.assertRedirects(response, reverse('login'))
        self.assertContains(response, '登録が完了しました')
        user = get_user_model().objects.get(username='newstudent')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(user.check_password(self.password))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_signup_errors_do_not_create_user(self):
        response = self.client.post(reverse('signup'), {
            'username': 'student', 'email': 'invalid',
            'password1': self.password, 'password2': 'different',
        })
        self.assertContains(response, 'role="alert"')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_login_returns_to_requested_page_and_logout_requires_post(self):
        self.assertRedirects(self.client.get(reverse('mypage')),
                             reverse('login') + '?next=/mypage/')
        response = self.client.post(reverse('login'), {
            'username': self.user.username, 'password': self.password,
            'next': reverse('mypage'),
        })
        self.assertRedirects(response, reverse('mypage'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), '/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_external_redirect(self):
        response = self.client.post(reverse('login'), {
            'username': self.user.username, 'password': self.password,
            'next': 'https://example.com/',
        })
        self.assertRedirects(response, '/')

    def test_invalid_login_displays_errors(self):
        response = self.client.post(reverse('login'), {
            'username': self.user.username, 'password': 'wrong',
        })
        self.assertContains(response, 'role="alert"')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_reset_email_and_password_change(self):
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse('password_reset_confirm', args=[uid, token])
        self.assertIn(url, mail.outbox[0].body)
        response = self.client.get(url)
        new_password = 'New-Pharmacy-934!'
        response = self.client.post(response.url, {
            'new_password1': new_password, 'new_password2': new_password,
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertContains(self.client.get(url), 'このリンクは無効')

    def test_unknown_email_has_same_confirmation(self):
        response = self.client.post(reverse('password_reset'), {'email': 'unknown@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_auth_pages_use_shared_layout(self):
        for name in ('login', 'signup', 'password_reset', 'password_reset_done', 'password_reset_complete'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'styles/auth.css')
                self.assertContains(response, 'id="auth-title"')
