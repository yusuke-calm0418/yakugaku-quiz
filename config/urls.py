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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from accounts.forms import EmailAuthenticationForm
from accounts.views import (
    home, mypage, signup, news_list, news_detail,
    verify_email, verification_sent, resend_verification,
)
from quiz.views import question_view, question_list_view, question_select_view

urlpatterns = [
    path('admin/', admin.site.urls),
    # トップページ
    path('', home, name='home'),
    
    # クイズ画面
    path('quiz/', question_view),
    path('quiz/select/', question_select_view, name='question_select'),
    # 問題集一覧画面
    path('questions/', question_list_view, name='question_list'),

    # ログイン系
    path('accounts/login/', auth_views.LoginView.as_view(authentication_form=EmailAuthenticationForm), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', signup, name='signup'),
    path('accounts/verify-email/<str:token>/', verify_email, name='verify_email'),
    path('accounts/verification-sent/', verification_sent, name='verification_sent'),
    path('accounts/resend-verification/', resend_verification, name='resend_verification'),
    
    path('news/', news_list, name='news_list'),
    path('news/<int:pk>/', news_detail, name='news_detail'),

    # マイページ
    path('mypage/', mypage, name='mypage'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
