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


class MyPageTests(TestCase):
    def setUp(self):
        from quiz.models import Question
        self.user = get_user_model().objects.create_user(username='learner')
        self.client.force_login(self.user)
        self.question = Question.objects.create(
            text='問題', choice1='1', choice2='2', choice3='3', choice4='4',
            correct='1', explanation='解説', category='pharmacology',
        )

    def answer(self, correct=False, user=None, when=None):
        from quiz.models import Answer
        answer = Answer.objects.create(user=user or self.user, question=self.question,
                                       selected=1, is_correct=correct)
        if when:
            Answer.objects.filter(pk=answer.pk).update(created_at=when)
        return answer

    def test_empty_dashboard(self):
        response = self.client.get(reverse('mypage'))
        self.assertContains(response, 'まだ学習の記録がありません')
        self.assertContains(response, 'styles/mypage.css')
        self.assertEqual(response.context['total'], 0)
        self.assertEqual(response.context['streak'], 0)
        self.assertEqual(len(response.context['subjects']), 7)

    def test_counts_progress_and_user_isolation(self):
        from accounts.services import learning_summary
        self.answer()
        self.answer()
        self.answer(correct=True)
        other = get_user_model().objects.create_user(username='other')
        self.answer(correct=True, user=other)
        summary = learning_summary(self.user)
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['correct'], 1)
        self.assertEqual(summary['accuracy'], 33)
        self.assertEqual(summary['weak_count'], 1)
        subject = next(row for row in summary['subjects'] if row['key'] == 'pharmacology')
        self.assertEqual(subject['answered'], 1)
        self.assertEqual(subject['progress'], 100)
        self.assertEqual(subject['accuracy'], 33)
        self.assertContains(self.client.get(reverse('mypage')), '苦手問題を復習する')

    def test_weak_threshold(self):
        from accounts.services import learning_summary
        self.answer()
        self.assertEqual(learning_summary(self.user)['weak_count'], 0)
        self.answer(correct=True)
        self.assertEqual(learning_summary(self.user)['weak_count'], 0)
        self.answer()
        self.assertEqual(learning_summary(self.user)['weak_count'], 1)

    def test_streak_uses_japanese_dates_and_distinct_days(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        from accounts.services import learning_summary
        # 9月10日 00:30 JST。UTCではまだ9月9日。
        now = datetime(2026, 9, 9, 15, 30, tzinfo=timezone.utc)
        with patch('django.utils.timezone.now', return_value=now):
            self.answer(when=datetime(2026, 9, 8, 16, tzinfo=timezone.utc))
            self.answer(when=datetime(2026, 9, 8, 17, tzinfo=timezone.utc))
            self.answer(when=datetime(2026, 9, 7, 16, tzinfo=timezone.utc))
            self.answer(when=datetime(2026, 9, 5, 16, tzinfo=timezone.utc))
            self.assertEqual(learning_summary(self.user)['streak'], 2)
            self.answer(when=now)
            self.assertEqual(learning_summary(self.user)['streak'], 3)
        with patch('django.utils.timezone.now', return_value=datetime(2026, 9, 12, tzinfo=timezone.utc)):
            self.assertEqual(learning_summary(self.user)['streak'], 0)
