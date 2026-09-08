from django.shortcuts import render, get_object_or_404
from .models import Question, Answer
import random

def question_view(request):
    result = None
    is_correct = None
    selected = []

    # ブックマーク切り替え処理（Ajax / フォーム）
    if request.GET.get('action') == 'toggle_bookmark':
        b_id = request.GET.get('question_id')
        if b_id:
            bookmarks = request.session.get('bookmarks', [])
            b_id_int = int(b_id) if b_id.isdigit() else b_id
            if b_id_int in bookmarks:
                bookmarks.remove(b_id_int)
            else:
                bookmarks.append(b_id_int)
            request.session['bookmarks'] = bookmarks
            request.session.modified = True

    # =========================
    # POST（回答処理）
    # =========================
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        question = get_object_or_404(Question, id=question_id)

        # 複数選択対応
        selected = request.POST.getlist('choice')  # ['1','3'] など

        # 正解データ（文字列→リスト化）
        correct_answers = list(question.correct)  # '13' → ['1','3']

        # 正誤判定（順不同対応）
        is_correct = sorted(selected) == sorted(correct_answers)

        # 履歴保存（ログイン時のみ）
        if request.user.is_authenticated:
            Answer.objects.create(
                user=request.user,
                question=question,
                selected="".join(selected),
                is_correct=is_correct
            )

        result = "正解！" if is_correct else "不正解..."

        # 同じ問題回避
        request.session['last_question_id'] = question.id

        # 進捗インクリメント
        quiz_progress = request.session.get('quiz_progress_index', 1)
        request.session['quiz_progress_index'] = quiz_progress + 1

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
                if category in ['physics', 'chemistry', 'biology']:
                    questions = questions.filter(category='physics_chemistry_biology')
                else:
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

    if not question:
        return render(request, 'quiz/question.html', {'question': None})

    # =========================
    # 正答率 & 進捗 & ブックマーク
    # =========================
    accuracy = 0
    if request.user.is_authenticated:
        answers = Answer.objects.filter(user=request.user)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        accuracy = int((correct / total) * 100) if total > 0 else 0

    bookmarks = request.session.get('bookmarks', [])
    is_bookmarked = question.id in bookmarks

    # 進捗管理（指定された問題数またはデフォルト30問）
    if request.GET.get('count'):
        try:
            total_quiz_count = int(request.GET.get('count'))
            request.session['quiz_total_count'] = total_quiz_count
            request.session['quiz_progress_index'] = 1
        except ValueError:
            total_quiz_count = request.session.get('quiz_total_count', 30)
    else:
        total_quiz_count = request.session.get('quiz_total_count', 30)

    progress_index = request.session.get('quiz_progress_index', 1)
    progress_percent = min(int((progress_index / total_quiz_count) * 100), 100)

    # カテゴリ表示名マッピング
    category_display_dict = dict(Question.CATEGORY_CHOICES)
    category_name = category_display_dict.get(question.category, '国家試験問題')

    # 選択肢リスト
    choices_list = [
        {'num': '1', 'text': question.choice1},
        {'num': '2', 'text': question.choice2},
        {'num': '3', 'text': question.choice3},
        {'num': '4', 'text': question.choice4},
    ]

    # 正解・選択のテキストリスト
    correct_choices_data = [c for c in choices_list if c['num'] in list(question.correct)]
    selected_choices_data = [c for c in choices_list if c['num'] in selected]

    return render(request, 'quiz/question.html', {
        'question': question,
        'result': result,
        'is_correct': is_correct,
        'correct_answer': list(question.correct),
        'selected_answers': selected,
        'choices_list': choices_list,
        'correct_choices_data': correct_choices_data,
        'selected_choices_data': selected_choices_data,
        'accuracy': accuracy,
        'is_bookmarked': is_bookmarked,
        'progress_index': progress_index,
        'total_quiz_count': total_quiz_count,
        'progress_percent': progress_percent,
        'category_name': category_name,
    })


def question_select_view(request):
    """
    問題・モード選択画面 (screenshots/question-select.png)
    """
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
    ]

    return render(request, 'quiz/question_select.html', {
        'categories': categories,
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

    
    