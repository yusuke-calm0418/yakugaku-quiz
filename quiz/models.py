from django.db import models
from django.contrib.auth.models import User

# Create your models here.
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
    
    text = models.TextField()
    choice1 = models.CharField(max_length=255)
    choice2 = models.CharField(max_length=255)
    choice3 = models.CharField(max_length=255)
    choice4 = models.CharField(max_length=255)
    correct = models.IntegerField()
    explanation = models.TextField()
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

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