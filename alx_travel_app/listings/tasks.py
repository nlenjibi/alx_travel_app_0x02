"""Celery tasks for the listings application."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Booking

logger = logging.getLogger(__name__)


def _build_payment_email_message(booking: Booking) -> tuple[str, str]:
    subject = f"Payment confirmed for booking #{booking.id}"
    message = (
        f"Hi {booking.user_name},\n\n"
        f"We have received your payment for {booking.listing.title} in {booking.listing.location}. "
        f"Your stay from {booking.start_date} to {booking.end_date} is now confirmed.\n\n"
        "Thank you for choosing ALX Travel!"
    )
    return subject, message


def send_payment_confirmation_email_sync(booking_id: int) -> None:
    """Send the payment confirmation email synchronously."""
    try:
        booking = Booking.objects.select_related('listing').get(pk=booking_id)
    except Booking.DoesNotExist:
        logger.warning("Tried to send payment email for missing booking %s", booking_id)
        return

    subject, message = _build_payment_email_message(booking)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@alxtravel.local')

    send_mail(
        subject,
        message,
        from_email,
        [booking.user_email],
        fail_silently=False,
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_payment_confirmation_email(self, booking_id: int) -> None:
    """Celery task wrapper for sending confirmation emails."""
    send_payment_confirmation_email_sync(booking_id)
