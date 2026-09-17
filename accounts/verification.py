"""Email identity, signed verification links, and provider-independent delivery."""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Trim
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerification

logger = logging.getLogger(__name__)
TOKEN_SALT = 'accounts.email-verification'


def normalize_email_address(email):
    return email.strip().lower()


def users_for_email(email):
    # Accommodate surrounding spaces in legacy records without rewriting them.
    return get_user_model().objects.alias(trimmed_email=Trim('email')).filter(
        trimmed_email__iexact=normalize_email_address(email),
    )


def verification_token(user):
    return signing.dumps({'user_id': user.pk, 'email': user.email}, salt=TOKEN_SALT)


def send_verification_email(user):
    """Reserve a send slot atomically; failed attempts also respect the cooldown."""
    now = timezone.now()
    cutoff = now - timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_INTERVAL)
    reserved = EmailVerification.objects.filter(
        user=user, verified_at__isnull=True, user__is_active=False,
    ).filter(Q(last_sent_at__isnull=True) | Q(last_sent_at__lte=cutoff)).update(last_sent_at=now)
    if not reserved:
        return True

    try:
        url = settings.SITE_URL + reverse('verify_email', args=[verification_token(user)])
        body = render_to_string('registration/verification_email.txt', {
            'verification_url': url,
            'timeout_hours': settings.EMAIL_VERIFICATION_TIMEOUT / 3600,
        })
        if send_mail('メールアドレスの確認 | 薬剤師国家試験対策', body,
                     settings.DEFAULT_FROM_EMAIL, [normalize_email_address(user.email)]) != 1:
            raise RuntimeError('Email backend did not accept the message')
    except Exception as exc:
        # Provider exceptions can contain request bodies, tokens, or credentials.
        logger.error('Verification email delivery failed (%s).', type(exc).__name__)
        return False
    return True


def verify_email_token(token):
    """Return invalid/complete/already without reactivating verified, suspended users."""
    if len(token) > 2048:
        return 'invalid'
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT)
    except (signing.BadSignature, ValueError, TypeError):
        return 'invalid'
    if (not isinstance(payload, dict) or type(payload.get('user_id')) is not int
            or not 0 < payload['user_id'] <= 9223372036854775807
            or not isinstance(payload.get('email'), str)):
        return 'invalid'

    with transaction.atomic():
        user = get_user_model().objects.select_for_update().filter(pk=payload['user_id']).first()
        if user is None or user.email != payload['email']:
            return 'invalid'
        verification = EmailVerification.objects.select_for_update().filter(user=user).first()
        if verification is None:
            return 'invalid'
        if verification.verified_at is not None:
            return 'already'
        if users_for_email(user.email).count() != 1:
            return 'invalid'
        verification.verified_at = timezone.now()
        verification.save(update_fields=['verified_at'])
        user.is_active = True
        user.save(update_fields=['is_active'])
    return 'complete'
