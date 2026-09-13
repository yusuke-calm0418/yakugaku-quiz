from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from tablib import Dataset

from .models import Answer, Question
from .resources import QUESTION_COLUMNS, REQUIRED_COLUMNS, QuestionResource


class QuestionCSVFixtures:
    def row(self, **changes):
        values = dict(zip(QUESTION_COLUMNS, (
            'TEST-001', '日本語の問題', '選択肢1', '選択肢2', '選択肢3', '選択肢4',
            '', '', '1', '説明, カンマあり\n改行あり', 'pharmacology', 'required',
        )))
        values.update(changes)
        return values

    def dataset(self, *rows, headers=QUESTION_COLUMNS):
        return Dataset(*[[row[name] for name in headers] for row in rows], headers=headers)


class QuestionImportTests(QuestionCSVFixtures, TestCase):
    def test_create_update_and_history_preserved(self):
        resource = QuestionResource()
        dataset = self.dataset(self.row(), self.row(question_code='TEST-002', question_type='general', correct='24'))
        self.assertFalse(resource.import_data(dataset).has_errors())
        question = Question.objects.get(question_code='TEST-001')
        user = get_user_model().objects.create_user(username='student')
        answer = Answer.objects.create(user=user, question=question, selected=1, is_correct=True)
        updated = self.row(text='更新した問題')
        result = resource.import_data(self.dataset(updated))
        self.assertEqual(result.totals['update'], 1)
        question.refresh_from_db()
        answer.refresh_from_db()
        self.assertEqual(question.text, updated['text'])
        self.assertEqual(answer.question_id, question.pk)
        self.assertEqual(Question.objects.count(), 2)

    def test_five_six_choices_and_legacy_csv_updates(self):
        resource = QuestionResource()
        rows = [self.row(question_code='FIVE', choice5='選択肢5', correct='5'),
                self.row(question_code='SIX', choice5='選択肢5', choice6='選択肢6', correct='6')]
        result = resource.import_data(self.dataset(*rows))
        self.assertFalse(result.has_errors())
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.get(question_code='FIVE').choice6, '')
        self.assertEqual(Question.objects.get(question_code='SIX').correct, '6')
        result = resource.import_data(self.dataset(self.row(question_code='SIX', text='更新', correct='6'), headers=REQUIRED_COLUMNS))
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.get(question_code='SIX').choice6, '選択肢6')
        result = resource.import_data(self.dataset(self.row(question_code='SIX', choice5='選択肢5', correct='5')))
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.get(question_code='SIX').choice6, '')
        self.assertEqual(Question.objects.count(), 2)
        result = resource.import_data(self.dataset(self.row(), headers=REQUIRED_COLUMNS))
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.get(question_code='TEST-001').choice5, '')

    def test_missing_correct_choice_and_invalid_extra_choices_rollback(self):
        for changes in ({'correct': '5'}, {'correct': '6', 'choice6': '   '},
                        {'choice5': 'x' * 256}, {'choice6': 'x' * 256},
                        {'choice5': '5', 'choice6': '6', 'correct': '56'},
                        {'choice5': '5', 'choice6': '6', 'correct': '556', 'question_type': 'general'}):
            with self.subTest(changes=changes):
                result = QuestionResource().import_data(self.dataset(self.row(question_code='OK'), self.row(**changes)))
                self.assertTrue(result.has_validation_errors())
                self.assertFalse(Question.objects.exists())

    def test_preview_does_not_save(self):
        result = QuestionResource().import_data(self.dataset(self.row()), dry_run=True)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.totals['new'], 1)
        self.assertFalse(Question.objects.exists())

    def test_reordered_headers_and_whitespace(self):
        result = QuestionResource().import_data(self.dataset(
            self.row(question_code=' TEST-001 ', correct=' 13 ', question_type=' general '),
            headers=tuple(reversed(QUESTION_COLUMNS)),
        ))
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.get().correct, '13')
        self.assertEqual(Question.objects.get().question_code, 'TEST-001')

    def test_invalid_values_rollback_creates_and_updates(self):
        QuestionResource().import_data(self.dataset(self.row()))
        invalid = [{name: '   '} for name in REQUIRED_COLUMNS]
        invalid += [dict(category='unknown'), dict(question_type='unknown'),
                    dict(question_code='x' * 51), dict(choice1='x' * 256)]
        invalid += [dict(correct=value) for value in ('0', '7', '12a', '11', '123', '12')]
        invalid += [dict(question_type='general', correct=value) for value in ('123', '11')]
        for changes in invalid:
            with self.subTest(changes=changes):
                bad = self.row(question_code='BAD')
                bad.update(changes)
                result = QuestionResource().import_data(self.dataset(
                    self.row(text='更新予定'), self.row(question_code='NEW'), bad,
                ))
                self.assertTrue(result.has_validation_errors())
                self.assertEqual(result.invalid_rows[0].number, 3)
                self.assertEqual(Question.objects.count(), 1)
                self.assertEqual(Question.objects.get().text, '日本語の問題')

    def test_duplicate_code_and_missing_or_duplicate_headers(self):
        datasets = [self.dataset(self.row(), self.row(question_code=' TEST-001 '))]
        datasets += [self.dataset(self.row(), headers=tuple(c for c in QUESTION_COLUMNS if c != name))
                     for name in REQUIRED_COLUMNS]
        datasets.append(self.dataset(self.row(), headers=QUESTION_COLUMNS + ('text',)))
        for dataset in datasets:
            with self.subTest(headers=dataset.headers):
                result = QuestionResource().import_data(dataset)
                self.assertTrue(result.has_errors() or result.has_validation_errors())
                self.assertFalse(Question.objects.exists())

    def test_legacy_questions_and_admin_blank_codes(self):
        from django.forms import modelform_factory
        form_class = modelform_factory(Question, fields='__all__')
        for _ in range(2):
            form = form_class(data=self.row(question_code=''))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertIsNone(form.save().question_code)


class QuestionImportAdminTests(QuestionCSVFixtures, TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(username='admin')
        self.client.force_login(self.admin_user)
        self.import_url = reverse('admin:quiz_question_import')
        self.confirm_url = reverse('admin:quiz_question_process_import')

    def upload(self, dataset, encoding='utf-8'):
        upload = SimpleUploadedFile('questions.csv', dataset.csv.encode(encoding), content_type='text/csv')
        return self.client.post(self.import_url, {'format': '0', 'import_file': upload})

    def test_upload_preview_confirm_and_reimport_utf8_bom(self):
        dataset = self.dataset(self.row(text='<script>alert(1)</script>'))
        for encoding in ('utf-8', 'utf-8-sig'):
            response = self.upload(dataset, encoding)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertIn('confirm_form', response.context)
            self.assertEqual(Question.objects.count(), 0 if encoding == 'utf-8' else 1)
            response = self.client.post(self.confirm_url, response.context['confirm_form'].initial)
            self.assertRedirects(response, reverse('admin:quiz_question_changelist'))
            self.assertEqual(Question.objects.count(), 1)
            self.assertEqual(Question.objects.get().explanation, self.row()['explanation'])

    def test_admin_upload_and_edit_extra_choices(self):
        rows = [self.row(question_code='FIVE', choice5='選択肢5', correct='5'),
                self.row(question_code='SIX', choice5='選択肢5', choice6='選択肢6', correct='6')]
        response = self.upload(self.dataset(*rows))
        self.assertIn('confirm_form', response.context)
        response = self.client.post(self.confirm_url, response.context['confirm_form'].initial)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.objects.count(), 2)
        question = Question.objects.get(question_code='SIX')
        url = reverse('admin:quiz_question_change', args=[question.pk])
        response = self.client.get(url)
        self.assertContains(response, 'name="choice5"')
        self.assertContains(response, 'name="choice6"')
        response = self.client.post(url, self.row(question_code='SIX', choice5='変更した5', correct='5'))
        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertEqual(question.choice5, '変更した5')
        self.assertEqual(question.choice6, '')
        response = self.client.post(reverse('admin:quiz_question_add'), self.row(question_code='NEW', choice6='選択肢6', correct='6'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.objects.get(question_code='NEW').correct, '6')

    def test_invalid_upload_displays_errors_without_confirmation(self):
        response = self.upload(self.dataset(self.row(), self.row(question_code='BAD', category='invalid')))
        self.assertContains(response, 'invalid')
        self.assertNotIn('confirm_form', response.context)
        self.assertFalse(Question.objects.exists())

    def test_confirmation_validation_failure_is_reported_and_rolled_back(self):
        from unittest.mock import patch
        response = self.upload(self.dataset(self.row(), self.row(question_code='SECOND')))
        original = QuestionResource.before_import_row

        def invalidate_second(resource, row, **kwargs):
            if row['question_code'] == 'SECOND':
                row['category'] = 'invalid'
            return original(resource, row, **kwargs)

        with patch.object(QuestionResource, 'before_import_row', invalidate_second):
            response = self.client.post(self.confirm_url, response.context['confirm_form'].initial)
        self.assertContains(response, '登録・更新されませんでした')
        self.assertContains(response, 'invalid')
        self.assertContains(response, self.import_url)
        self.assertFalse(Question.objects.exists())

    def test_import_permissions_and_csrf(self):
        from django.test import Client
        for staff in (False, True):
            user = get_user_model().objects.create_user(username=f'user-{staff}', is_staff=staff)
            self.client.force_login(user)
            for url in (self.import_url, self.confirm_url):
                response = self.client.post(url)
                self.assertEqual(response.status_code, 403 if staff else 302)
        user.user_permissions.add(Permission.objects.get(codename='change_question'))
        self.assertEqual(self.client.get(self.import_url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename='add_question'))
        self.assertEqual(self.client.get(self.import_url).status_code, 200)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_user)
        self.assertEqual(client.post(self.import_url).status_code, 403)
        self.assertEqual(client.post(self.confirm_url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.import_url).status_code, 302)

    def test_existing_admin_pages_and_sample(self):
        self.assertContains(self.client.get(reverse('admin:quiz_question_changelist')), self.import_url)
        self.assertEqual(self.client.get(reverse('admin:quiz_question_add')).status_code, 200)
        sample = Path(__file__).resolve().parent.parent / 'docs/features/samples/questions-import-sample.csv'
        result = QuestionResource().import_data(Dataset().load(sample.read_text(), format='csv'))
        self.assertFalse(result.has_errors())
        self.assertFalse(result.has_validation_errors())
        self.assertEqual(Question.objects.count(), 2)
        question = Question.objects.first()
        for action in ('change', 'delete'):
            self.assertEqual(self.client.get(reverse(f'admin:quiz_question_{action}', args=[question.pk])).status_code, 200)
