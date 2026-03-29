from django.shortcuts import render
from quiz.models import Answer

def home(request):
    return render(request, 'home.html')

def mypage(request):
    answers = Answer.objects.filter(user=request.user)

    total = answers.count()
    correct = answers.filter(is_correct=True).count()

    accuracy = int((correct / total) * 100) if total > 0 else 0

    # 苦手問題数（正答率50%未満）
    from django.db.models import Count, Q

    stats = answers.values('question').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    )

    weak_count = 0
    for s in stats:
        if s['correct'] / s['total'] < 0.5:
            weak_count += 1

    return render(request, 'mypage.html', {
        'total': total,
        'correct': correct,
        'accuracy': accuracy,
        'weak_count': weak_count
    })