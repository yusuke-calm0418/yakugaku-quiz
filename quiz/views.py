from django.shortcuts import render, get_object_or_404
from .models import Question, Answer
import random

def question_view(request):
    result = None
    is_correct = None

    # POST（回答時）
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        question = get_object_or_404(Question, id=question_id)

        selected = int(request.POST.get('choice'))
        is_correct = selected == question.correct

        # 履歴保存
        Answer.objects.create(
            user=request.user,
            question=question,
            selected=selected,
            is_correct=is_correct
        )

        result = "正解！" if is_correct else "不正解..."

        request.session['last_question_id'] = question.id

    # GET（問題取得）
    else:
        mode = request.GET.get('mode')
        category = request.GET.get('category') 

        if mode == 'weak':
            from django.db.models import Count, Q

    # 🔥 問題ごとの正答率を計算
            stats = Answer.objects.filter(user=request.user).values('question').annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True))
            )

            weak_ids = []

            for s in stats:
                accuracy = s['correct'] / s['total']
                if s['total'] >= 2 and accuracy < 0.5:  # 🔥 50%未満を苦手
                    weak_ids.append(s['question'])

            questions = Question.objects.filter(id__in=weak_ids)

        else:
            questions = Question.objects.all()
            
        if category:
            questions = questions.filter(category=category)

        if not questions:
            return render(request, 'quiz/question.html', {'question': None})

        last_id = request.session.get('last_question_id')
        if last_id:
            questions = questions.exclude(id=last_id)

        if not questions:
            questions = Question.objects.all()

        question = random.choice(list(questions))

    # 正答率
    answers = Answer.objects.filter(user=request.user)
    total = answers.count()
    correct = answers.filter(is_correct=True).count()

    accuracy = int((correct / total) * 100) if total > 0 else 0

    return render(request, 'quiz/question.html', {
        'question': question,
        'result': result,
        'is_correct': is_correct,
        'correct_answer': question.correct,
        'accuracy': accuracy
    })