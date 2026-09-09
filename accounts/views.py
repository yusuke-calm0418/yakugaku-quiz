from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import News
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignupForm
from .services import learning_summary

def home(request):
    return render(request, 'home.html', {'latest_news': News.objects.published()[:3]})

@login_required
def mypage(request):
    context = learning_summary(request.user)
    context['latest_news'] = News.objects.published()[:3]
    return render(request, 'mypage.html', context)

def signup(request):
    if request.user.is_authenticated:
        return redirect('mypage')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '登録が完了しました。ユーザー名とパスワードでログインしてください。')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'registration/signup.html', {'form': form})

def news_list(request):
    page = Paginator(News.objects.published(), 10).get_page(request.GET.get('page'))
    return render(request, 'news/list.html', {'page_obj': page})


def news_detail(request, pk):
    news = get_object_or_404(News.objects.published(), pk=pk)
    return render(request, 'news/detail.html', {'news': news})
