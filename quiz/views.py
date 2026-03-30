from django.shortcuts import render, get_object_or_404
from .models import Question, Answer
import random

def question_view(request):
    result = None
    is_correct = None

    # =========================
    # POST（回答処理）
    # =========================
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        question = get_object_or_404(Question, id=question_id)

        # 🔥 複数選択対応
        selected = request.POST.getlist('choice')  # ['1','3'] など

        # 正解データ（文字列→リスト化）
        correct_answers = list(question.correct)  # '13' → ['1','3']

        # 正誤判定（順不同対応）
        is_correct = sorted(selected) == sorted(correct_answers)

        # 履歴保存（文字列で保存）
        Answer.objects.create(
            user=request.user,
            question=question,
            selected="".join(selected),  # '13'みたいに保存
            is_correct=is_correct
        )

        result = "正解！" if is_correct else "不正解..."

        # 同じ問題回避
        request.session['last_question_id'] = question.id

    # =========================
    # GET（問題取得）
    # =========================
    else:
        mode = request.GET.get('mode')
        category = request.GET.get('category')
        q_type = request.GET.get('type')  # 🔥 必須/一般

        # 苦手モード
        if mode == 'weak':
            from django.db.models import Count, Q

            stats = Answer.objects.filter(user=request.user).values('question').annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True))
            )

            weak_ids = []

            for s in stats:
                accuracy = s['correct'] / s['total']
                if s['total'] >= 2 and accuracy < 0.5:
                    weak_ids.append(s['question'])

            questions = Question.objects.filter(id__in=weak_ids)

        else:
            questions = Question.objects.all()

        # 分野フィルター
        if category:
            questions = questions.filter(category=category)

        # 必須 / 一般フィルター
        if q_type:
            questions = questions.filter(question_type=q_type)

        # 問題なし対策
        if not questions:
            return render(request, 'quiz/question.html', {'question': None})

        # 同じ問題回避
        last_id = request.session.get('last_question_id')
        if last_id:
            questions = questions.exclude(id=last_id)

        if not questions:
            questions = Question.objects.all()

        question = random.choice(list(questions))

    # =========================
    # 正答率
    # =========================
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
    
    