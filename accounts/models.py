from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class EmailVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='email_verification')
    verified_at = models.DateTimeField(null=True, blank=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NewsQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, published_at__lte=timezone.now())


class News(models.Model):
    title = models.CharField('タイトル', max_length=200)
    body = models.TextField('本文', help_text='改行を反映します。HTMLタグは使用できません。')
    is_published = models.BooleanField('公開する', default=False)
    published_at = models.DateTimeField('公開日時', default=timezone.now,
                                        help_text='未来の日時を指定すると、その日時から表示されます。')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    objects = NewsQuerySet.as_manager()

    class Meta:
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'
        ordering = ['-published_at', '-pk']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news_detail', args=[self.pk])
