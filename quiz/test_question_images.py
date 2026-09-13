from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Question
from .resources import QuestionResource
from .test_csv_import import QuestionCSVFixtures


class QuestionImageTests(QuestionCSVFixtures, TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.client.force_login(get_user_model().objects.create_superuser(username='image-admin'))

    def upload(self, format='PNG'):
        data = BytesIO()
        Image.new('RGB', (1200, 600), 'white').save(data, format=format)
        return SimpleUploadedFile(f'diagram.{format.lower()}', data.getvalue(), content_type=f'image/{format.lower()}')

    def test_admin_add_replace_clear_and_optional_image(self):
        url = reverse('admin:quiz_question_add')
        response = self.client.post(url, self.row(question_image=self.upload()))
        self.assertEqual(response.status_code, 302)
        question = Question.objects.get()
        self.assertTrue(question.question_image.storage.exists(question.question_image.name))
        old_name = question.question_image.name
        url = reverse('admin:quiz_question_change', args=[question.pk])
        response = self.client.post(url, self.row(question_image=self.upload('JPEG')))
        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertNotEqual(question.question_image.name, old_name)
        response = self.client.post(url, {**self.row(), 'question_image-clear': 'on'})
        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertFalse(question.question_image)
        self.assertNotContains(self.client.get('/quiz/', {'question_id': question.pk}), 'class="question-image"')

    def test_invalid_and_oversized_upload_rejected(self):
        invalid = SimpleUploadedFile('fake.png', b'<html>not an image</html>', content_type='image/png')
        large = self.upload()
        large.size = 5 * 1024 * 1024 + 1
        # ModelForm validation avoids transmitting a synthetic 5MB body in the test.
        from django.forms import modelform_factory
        form_class = modelform_factory(Question, fields='__all__')
        for upload in (invalid, large):
            form = form_class(self.row(), {'question_image': upload})
            self.assertFalse(form.is_valid())
            self.assertIn('question_image', form.errors)
        self.assertFalse(Question.objects.exists())

    def test_display_order_and_grading_with_five_six_choices(self):
        for count, format in ((5, 'PNG'), (6, 'WEBP')):
            question = Question.objects.create(**self.row(
                question_code=f'IMAGE-{count}', choice5='選択肢5',
                choice6='選択肢6' if count == 6 else '', correct=str(count),
                question_image=self.upload(format),
            ))
            response = self.client.get('/quiz/', {'question_id': question.pk})
            self.assertContains(response, question.question_image.url)
            html = response.content.decode()
            self.assertLess(html.index('id="question-title"'), html.index('class="question-image"'))
            self.assertLess(html.index('class="question-image"'), html.index('class="quiz-choices"'))
            self.assertEqual(len(response.context['choices_list']), count)
            response = self.client.post('/quiz/', {'question_id': question.pk, 'choice': str(count)})
            self.assertTrue(response.context['is_correct'])
            self.assertContains(response, question.question_image.url)

    def test_csv_update_preserves_image(self):
        question = Question.objects.create(**self.row(question_image=self.upload()))
        name = question.question_image.name
        result = QuestionResource().import_data(self.dataset(self.row(text='更新後')))
        self.assertFalse(result.has_errors())
        self.assertFalse(result.has_validation_errors())
        question.refresh_from_db()
        self.assertEqual(question.question_image.name, name)
        self.assertEqual(question.text, '更新後')

    @override_settings(DEBUG=True)
    def test_development_media_serving(self):
        # Build development URL patterns with the temporary MEDIA_ROOT.
        from django.conf import settings
        from django.conf.urls.static import static
        from types import ModuleType
        urls = ModuleType('image_test_urls')
        urls.urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        question = Question.objects.create(**self.row(question_image=self.upload()))
        with override_settings(ROOT_URLCONF=urls):
            response = self.client.get(question.question_image.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))
