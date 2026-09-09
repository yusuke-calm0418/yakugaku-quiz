from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignupForm
from .services import learning_summary

def home(request):
    return render(request, 'home.html')

@login_required
def mypage(request):
    return render(request, 'mypage.html', learning_summary(request.user))

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