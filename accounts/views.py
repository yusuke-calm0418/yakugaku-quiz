from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ResendVerificationForm, SignupForm
from .models import EmailVerification, News
from .services import learning_summary
from .verification import send_verification_email, users_for_email, verify_email_token


def home(request):
    return render(request, 'home.html', {'latest_news': News.objects.published()[:3]})


@login_required
def mypage(request):
    context = learning_summary(request.user)
    context['latest_news'] = News.objects.published()[:3]
    return render(request, 'mypage.html', context)


@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('mypage')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                EmailVerification.objects.create(user=user)
            if not send_verification_email(user):
                return render(request, 'registration/verification_sent.html', {'send_failed': True})
            return redirect('verification_sent')
    else:
        form = SignupForm()

    return render(request, 'registration/signup.html', {'form': form})


@never_cache
@require_GET
def verify_email(request, token):
    result = verify_email_token(token)
    template = 'verification_invalid' if result == 'invalid' else 'verification_complete'
    response = render(request, f'registration/{template}.html', {'already_verified': result == 'already'})
    response['Referrer-Policy'] = 'no-referrer'
    return response


@require_GET
def verification_sent(request):
    return render(request, 'registration/verification_sent.html')


@require_http_methods(['GET', 'POST'])
def resend_verification(request):
    form = ResendVerificationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        candidates = list(users_for_email(form.cleaned_data['email'])[:2])
        if len(candidates) == 1:
            send_verification_email(candidates[0])
        # The same response includes retry guidance even when delivery fails.
        return redirect('verification_sent')
    return render(request, 'registration/resend_verification.html', {'form': form})


def news_list(request):
    page = Paginator(News.objects.published(), 10).get_page(request.GET.get('page'))
    return render(request, 'news/list.html', {'page_obj': page})


def news_detail(request, pk):
    news = get_object_or_404(News.objects.published(), pk=pk)
    return render(request, 'news/detail.html', {'news': news})
