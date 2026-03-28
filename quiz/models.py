from django.db import models

# Create your models here.
class Question(models.Model):
    text = models.TextField()
    choice1 = models.CharField(max_length=255)
    choice2 = models.CharField(max_length=255)
    choice3 = models.CharField(max_length=255)
    choice4 = models.CharField(max_length=255)
    correct = models.IntegerField()
    explanation = models.TextField()

    def __str__(self):
        return self.text[:50]