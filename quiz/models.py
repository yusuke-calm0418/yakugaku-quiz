from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

def validate_question_image_size(image):
    if image and not image._committed and image.size > 5 * 1024 * 1024:
        raise ValidationError('問題画像は5MB以下にしてください。')


class Question(models.Model):
    CATEGORY_CHOICES = [
        ('physics_chemistry_biology', '物理・化学・生物'),
        ('hygiene', '衛生'),
        ('pharmacology', '薬理'),
        ('pharmaceutics', '薬剤'),
        ('pathology', '病態・薬物治療'),
        ('law_ethics', '法規・制度・倫理'),
        ('practice', '実務'),
    ]
    QUESTION_TYPE_CHOICES = [
        ('required', '必須問題'),
        ('general', '一般問題'),
    ]
    question_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    text = models.TextField()
    question_image = models.ImageField(
        upload_to='questions/', blank=True, null=True,
        validators=[validate_question_image_size],
        help_text='問題図（PNG・JPEG・WebP、5MB以下）。省略できます。',
    )
    choice1 = models.CharField(max_length=255)
    choice2 = models.CharField(max_length=255)
    choice3 = models.CharField(max_length=255)
    choice4 = models.CharField(max_length=255)
    choice5 = models.CharField(max_length=255, blank=True, default='')
    choice6 = models.CharField(max_length=255, blank=True, default='')
    correct = models.CharField(max_length=10) 
    explanation = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='general'
    )

    @property
    def choices_list(self):
        return [
            {'num': str(number), 'text': value}
            for number in range(1, 7)
            if (value := getattr(self, f'choice{number}')).strip()
        ]

    def clean(self):
        super().clean()
        correct = self.correct or ''
        error = None
        if not correct or any(value not in '123456' for value in correct):
            error = '正解番号は1〜6のみ指定できます。'
        elif len(set(correct)) != len(correct):
            error = '同じ正解番号を重複して指定できません。'
        elif self.question_type == 'required' and len(correct) != 1:
            error = '必須問題の正解は1つ指定してください。'
        elif self.question_type == 'general' and len(correct) > 2:
            error = '一般問題の正解は1つまたは2つ指定してください。'
        elif any(value not in {choice['num'] for choice in self.choices_list} for value in correct):
            error = '空欄の選択肢を正解に指定できません。'
        if error:
            raise ValidationError({'correct': error})

    def __str__(self):
        return self.text[:50]

class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected = models.IntegerField()
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.question.id}"
