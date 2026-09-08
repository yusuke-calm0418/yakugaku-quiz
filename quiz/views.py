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
        specific_id = request.GET.get('question_id')
        mode = request.GET.get('mode')
        category = request.GET.get('category')
        q_type = request.GET.get('type')  # 必須/一般

        if specific_id:
            question = Question.objects.filter(id=specific_id).first()
        else:
            # 苦手モード
            if mode == 'weak':
                from django.db.models import Count, Q

                if request.user.is_authenticated:
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
                    questions = Question.objects.none()
            else:
                questions = Question.objects.all()

            # 分野フィルター
            if category:
                questions = questions.filter(category=category)

            # 必須 / 一般フィルター
            if q_type:
                questions = questions.filter(question_type=q_type)

            # 問題なし対策
            if not questions.exists():
                return render(request, 'quiz/question.html', {'question': None})

            # 同じ問題回避
            last_id = request.session.get('last_question_id')
            if last_id and questions.count() > 1:
                questions = questions.exclude(id=last_id)

            question = random.choice(list(questions))

    # =========================
    # 正答率
    # =========================
    accuracy = 0
    if request.user.is_authenticated:
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


def question_list_view(request):
    """
    問題集一覧ビュー: 分野別 / 苦手一覧 / ブックマーク対応
    """
    from django.core.paginator import Paginator
    from django.db.models import Count, Q

    tab = request.GET.get('tab', 'category')
    category = request.GET.get('category', 'all')

    questions_qs = Question.objects.all().order_id_asc() if hasattr(Question.objects, 'order_id_asc') else Question.objects.all().order_by('id')

    # タブごとの分岐
    if tab == 'weak':
        if request.user.is_authenticated:
            stats = Answer.objects.filter(user=request.user).values('question').annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True))
            )
            weak_ids = [
                s['question'] for s in stats 
                if s['total'] >= 2 and (s['correct'] / s['total']) < 0.5
            ]
            questions_qs = questions_qs.filter(id__in=weak_ids)
        else:
            questions_qs = Question.objects.none()

    elif tab == 'bookmark':
        bookmarks = request.session.get('bookmarks', [])
        questions_qs = questions_qs.filter(id__in=bookmarks)

    else:
        # 分野別フィルター
        if category and category != 'all':
            if category in ['physics', 'chemistry', 'biology']:
                # 物理・化学・生物
                questions_qs = questions_qs.filter(
                    Q(category='physics_chemistry_biology') |
                    Q(category=category)
                )
            else:
                questions_qs = questions_qs.filter(category=category)

    # ページネーション
    paginator = Paginator(questions_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # カテゴリ定義一覧
    categories = [
        {'code': 'physics', 'name': '物理'},
        {'code': 'chemistry', 'name': '化学'},
        {'code': 'biology', 'name': '生物'},
        {'code': 'hygiene', 'name': '衛生'},
        {'code': 'pharmacology', 'name': '薬理'},
        {'code': 'pharmaceutics', 'name': '薬剤'},
        {'code': 'pathology', 'name': '病態・薬物治療'},
        {'code': 'law_ethics', 'name': '法規・制度・倫理'},
        {'code': 'practice', 'name': '実務'},
        {'code': 'all', 'name': '全て'},
    ]

    return render(request, 'quiz/question_list.html', {
        'page_obj': page_obj,
        'tab': tab,
        'current_category': category,
        'categories': categories,
        'total_count': questions_qs.count(),
    })

    
    