import json
import os
from pathlib import Path
import runpy
from unittest.mock import patch

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import EmailVerification
from .verification import send_verification_email


class EmailSettingsTests(SimpleTestCase):
    def load_settings(self, **env):
        with patch.dict(os.environ, {'SECRET_KEY': 'test-settings-only', **env}, clear=True):
            return runpy.run_path(str(Path(settings.BASE_DIR) / 'config/settings.py'))

    def test_local_defaults(self):
        config = self.load_settings()
        self.assertEqual(config['EMAIL_BACKEND'], 'django.core.mail.backends.console.EmailBackend')
        self.assertEqual(config['SITE_URL'], 'http://localhost:8000')
        self.assertEqual(config['EMAIL_VERIFICATION_TIMEOUT'], 86400)
        self.assertEqual(config['EMAIL_VERIFICATION_RESEND_INTERVAL'], 60)

    def test_render_resend_and_origin(self):
        config = self.load_settings(RENDER='true', RENDER_EXTERNAL_HOSTNAME='quiz.onrender.com',
            EMAIL_PROVIDER='resend', RESEND_API_KEY='test-api-key', DEFAULT_FROM_EMAIL='quiz@example.com')
        self.assertFalse(config['DEBUG'])
        self.assertEqual(config['EMAIL_BACKEND'], 'anymail.backends.resend.EmailBackend')
        self.assertEqual(config['ANYMAIL']['RESEND_API_KEY'], 'test-api-key')
        self.assertEqual(config['ANYMAIL']['REQUESTS_TIMEOUT'], 10)
        self.assertEqual(config['SITE_URL'], 'https://quiz.onrender.com')
        self.assertIn('anymail', config['INSTALLED_APPS'])

    def test_site_url_and_timeouts_can_be_configured(self):
        config = self.load_settings(SITE_URL='https://quiz.example.com/',
            EMAIL_VERIFICATION_TIMEOUT='3600', EMAIL_VERIFICATION_RESEND_INTERVAL='120')
        self.assertEqual(config['SITE_URL'], 'https://quiz.example.com')
        self.assertEqual(config['EMAIL_VERIFICATION_TIMEOUT'], 3600)
        self.assertEqual(config['EMAIL_VERIFICATION_RESEND_INTERVAL'], 120)

    def test_bad_provider_or_missing_resend_credentials_fail_early(self):
        for env in [{'EMAIL_PROVIDER': 'smtp'}, {'EMAIL_PROVIDER': 'resend'},
                    {'EMAIL_PROVIDER': 'resend', 'RESEND_API_KEY': 'test-key'},
                    {'EMAIL_PROVIDER': 'resend', 'DEFAULT_FROM_EMAIL': 'quiz@example.com'}]:
            with self.subTest(env_keys=list(env)):
                with self.assertRaises(ImproperlyConfigured):
                    self.load_settings(**env)

    def test_invalid_origins_and_intervals_are_rejected(self):
        for origin in ['javascript:alert(1)', 'https://example.com/path', 'https://user:pass@example.com',
                       'https://example.com?query=1', 'https://example.com#fragment', '']:
            with self.subTest(origin=origin):
                with self.assertRaises(ImproperlyConfigured):
                    self.load_settings(SITE_URL=origin)
        with self.assertRaises(ImproperlyConfigured):
            self.load_settings(RENDER='true', SITE_URL='http://example.com')
        for name in ['EMAIL_VERIFICATION_TIMEOUT', 'EMAIL_VERIFICATION_RESEND_INTERVAL']:
            with self.assertRaises(ImproperlyConfigured):
                self.load_settings(**{name: '0'})


@override_settings(EMAIL_BACKEND='anymail.backends.resend.EmailBackend',
                   ANYMAIL={'RESEND_API_KEY': 'test-key-not-real', 'REQUESTS_TIMEOUT': 10},
                   DEFAULT_FROM_EMAIL='quiz@example.com', SITE_URL='https://quiz.example.com')
class ResendBackendTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='internal', email='reader@example.com',
            password='Study-Pharmacy-482!', is_active=False)
        EmailVerification.objects.create(user=self.user)

    def api_response(self, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = json.dumps({'id': 'test-message-id'} if status == 200 else {
            'name': 'validation_error', 'message': 'provider-private-details',
        }).encode()
        response.headers['Content-Type'] = 'application/json'
        return response

    def test_verification_and_password_reset_use_resend_https_backend(self):
        with patch('requests.Session.request', return_value=self.api_response()) as request:
            self.assertTrue(send_verification_email(self.user))
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])
            self.client.post(reverse('password_reset'), {'email': self.user.email})
        self.assertEqual(request.call_count, 2)
        for call in request.call_args_list:
            self.assertEqual(call.kwargs['url'], 'https://api.resend.com/emails')
            self.assertEqual(call.kwargs['method'].upper(), 'POST')
            self.assertEqual(call.kwargs['timeout'], 10)
            payload = json.loads(call.kwargs['data'])
            self.assertEqual(payload['from'], 'quiz@example.com')
            self.assertEqual(payload['to'], ['reader@example.com'])
            self.assertNotIn(self.user.username, payload['text'])
        verification = json.loads(request.call_args_list[0].kwargs['data'])
        self.assertIn('https://quiz.example.com/accounts/verify-email/', verification['text'])
        reset = json.loads(request.call_args_list[1].kwargs['data'])
        self.assertIn('/accounts/reset/', reset['text'])

    def test_resend_http_failure_does_not_leak_provider_response(self):
        with patch('requests.Session.request', return_value=self.api_response(403)):
            with self.assertLogs('accounts.verification', level='ERROR') as logs:
                self.assertFalse(send_verification_email(self.user))
        self.assertNotIn('provider-private-details', '\n'.join(logs.output))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNone(self.user.email_verification.verified_at)
