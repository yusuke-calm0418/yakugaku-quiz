from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Answer, Question


class QuizTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='student')
        self.client.force_login(self.user)
        self.question = Question.objects.create(text='問題文', choice1='選択肢1', choice2='選択肢2',
            choice3='選択肢3', choice4='選択肢4', correct='1', explanation='解説文',
            category='pharmacology', question_type='required')

    def test_question_and_result(self):
        response = self.client.get('/quiz/?count=10&category=pharmacology')
        self.assertContains(response, 'styles/quiz.css')
        self.assertNotContains(response, '解説文')
        response = self.client.post('/quiz/?count=10&category=pharmacology', {'question_id': self.question.pk, 'choice': '1'})
        self.assertContains(response, '○ 正解！')
        self.assertContains(response, '解説文')
        self.assertEqual(response.context['progress_index'], 1)
        self.assertEqual(response.context['next_url'], '/quiz/?category=pharmacology')
        self.assertEqual(Answer.objects.count(), 1)
        response = self.client.get(response.context['next_url'])
        self.assertEqual(response.context['progress_index'], 2)

    def test_invalid_answers_are_not_saved(self):
        for choices in ([], ['1', '2'], ['5'], ['abc'], ['1', '1']):
            response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': choices})
            self.assertContains(response, '選択肢を1つ選んでください。')
        self.assertEqual(Answer.objects.count(), 0)

    def test_multiple_answers_and_wrong_result(self):
        self.question.question_type = 'general'
        self.question.correct = '13'
        self.question.save()
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': ['3', '1']})
        self.assertTrue(response.context['is_correct'])
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': ['2']})
        self.assertContains(response, '× 不正解')
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': ['1', '2', '3']})
        self.assertIsNotNone(response.context['error'])
        self.assertEqual(Answer.objects.count(), 2)

    def test_count_bounds_and_completion(self):
        for count in ('0', '-1', 'bad', '100000'):
            response = self.client.get('/quiz/', {'count': count})
            self.assertEqual(response.status_code, 200)
            self.assertGreaterEqual(response.context['total_quiz_count'], 1)
            self.assertLessEqual(response.context['total_quiz_count'], 100)
        self.client.get('/quiz/?count=1')
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': '1'})
        self.assertContains(response, '1問の演習が完了しました')

    def test_bookmark_post_does_not_answer_or_change_question(self):
        self.client.get('/quiz/?count=10')
        payload = {'action': 'toggle_bookmark', 'question_id': self.question.pk}
        self.assertTrue(self.client.post('/quiz/', payload).json()['bookmarked'])
        self.assertIn(self.question.pk, self.client.session['bookmarks'])
        self.assertFalse(self.client.post('/quiz/', payload).json()['bookmarked'])
        self.assertEqual(Answer.objects.count(), 0)
        self.assertEqual(self.client.session['quiz_progress_index'], 1)

    def test_empty_and_filters(self):
        self.assertContains(self.client.get('/quiz/?category=hygiene'), '出題できる問題がありません')
        self.assertContains(self.client.get('/quiz/?question_type=general'), '出題できる問題がありません')
        self.assertEqual(self.client.get('/quiz/?question_id=invalid').status_code, 404)

    def test_guest_answers_are_not_saved(self):
        self.client.logout()
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': '1'})
        self.assertContains(response, '○ 正解！')
        self.assertEqual(Answer.objects.count(), 0)

    def test_five_and_six_choices_display_and_grading(self):
        for count in (5, 6):
            with self.subTest(count=count):
                self.question.choice5 = '追加選択肢5'
                self.question.choice6 = '追加選択肢6' if count == 6 else ''
                self.question.correct = str(count)
                self.question.full_clean()
                self.question.save()
                response = self.client.get('/quiz/', {'question_id': self.question.pk})
                self.assertEqual(len(response.context['choices_list']), count)
                self.assertContains(response, 'type="radio"', count=count)
                self.assertContains(response, '追加選択肢5')
                if count == 5:
                    self.assertNotContains(response, 'value="6"')
                else:
                    self.assertContains(response, '追加選択肢6')
                response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': str(count)})
                self.assertTrue(response.context['is_correct'])
                self.assertEqual(response.context['correct_choices_data'][0]['num'], str(count))
                answer = Answer.objects.latest('pk')
                self.assertTrue(answer.is_correct)
                self.assertEqual(answer.selected, count)

    def test_optional_choices_and_selection_limits(self):
        self.question.choice5 = '選択肢5'
        self.question.choice6 = '   '
        self.question.save()
        for choices in (['6'], ['7'], ['5', '1'], ['5', '5']):
            response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': choices})
            self.assertIsNotNone(response.context['error'])
        self.assertFalse(Answer.objects.exists())
        self.question.choice6 = '選択肢6'
        self.question.question_type = 'general'
        self.question.correct = '56'
        self.question.save()
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': ['6', '5']})
        self.assertTrue(response.context['is_correct'])
        response = self.client.post('/quiz/', {'question_id': self.question.pk, 'choice': ['1', '5', '6']})
        self.assertIsNotNone(response.context['error'])
        self.assertEqual(Answer.objects.count(), 1)
