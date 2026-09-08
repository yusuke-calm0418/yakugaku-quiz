"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from accounts.views import home, mypage, signup
from quiz.views import question_view, question_list_view, question_select_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # トップページ
    path('', home),
    
    # クイズ画面
    path('quiz/', question_view),
    path('quiz/select/', question_select_view, name='question_select'),
    # 問題集一覧画面
    path('questions/', question_list_view, name='question_list'),

    # ログイン系
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', signup),
    
    # マイページ
    path('mypage/', mypage),
]
