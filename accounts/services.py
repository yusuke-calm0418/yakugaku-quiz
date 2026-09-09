from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from quiz.models import Answer, Question


def learning_summary(user):
    answers = Answer.objects.filter(user=user)
    totals = answers.aggregate(total=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
    total = totals['total']
    categories = {
        row['question__category']: row
        for row in answers.values('question__category').annotate(
            total=Count('id'), correct=Count('id', filter=Q(is_correct=True)),
            answered=Count('question_id', distinct=True),
        )
    }
    available = dict(Question.objects.values('category').annotate(count=Count('id')).values_list('category', 'count'))
    subjects = []
    for key, label in Question.CATEGORY_CHOICES:
        stats = categories.get(key, {'total': 0, 'correct': 0, 'answered': 0})
        count = available.get(key, 0)
        subjects.append({
            **stats, 'key': key, 'label': label, 'available': count,
            'progress': int(stats['answered'] * 100 / count) if count else 0,
            'accuracy': int(stats['correct'] * 100 / stats['total']) if stats['total'] else 0,
        })

    question_stats = answers.values('question_id').annotate(
        total=Count('id'), correct=Count('id', filter=Q(is_correct=True)),
    )
    weak_count = sum(row['total'] >= 2 and row['correct'] * 2 < row['total'] for row in question_stats)

    japan = ZoneInfo('Asia/Tokyo')
    today = timezone.localdate(timezone=japan)
    days = answers.annotate(day=TruncDate('created_at', tzinfo=japan)).values_list('day', flat=True).distinct().order_by('-day')
    streak = 0
    expected = today
    for day in days:
        if not streak and day == today - timedelta(days=1):
            expected = day
        if day != expected:
            break
        streak += 1
        expected -= timedelta(days=1)

    return {
        **totals, 'accuracy': int(totals['correct'] * 100 / total) if total else 0,
        'subjects': subjects, 'streak': streak, 'weak_count': weak_count,
    }
