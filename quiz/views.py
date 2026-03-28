from django.shortcuts import render, get_object_or_404
from .models import Question
import random

def question_view(request):
    result = None
    is_correct = None

    if request.method == 'POST':
        question_id = request.POST.get('question_id')

        print("question_id:", question_id)

        # 安全に取得
        question = get_object_or_404(Question, id=int(question_id))

        selected = int(request.POST.get('choice'))

        if selected == question.correct:
            result = "正解！"
            is_correct = True
        else:
            result = "不正解..."
            is_correct = False

    else:
        questions = Question.objects.all()
        question = random.choice(questions)

    return render(request, 'quiz/question.html', {
        'question': question,
        'result': result,
        'is_correct': is_correct
    })