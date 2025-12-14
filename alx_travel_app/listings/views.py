import logging
import uuid

import requests
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer
from .tasks import send_payment_confirmation_email, send_payment_confirmation_email_sync

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
	"""Raised when interactions with the Chapa API fail."""


class ListingViewSet(viewsets.ModelViewSet):
	queryset = Listing.objects.all().order_by('-created_at')
	serializer_class = ListingSerializer


class BookingViewSet(viewsets.ModelViewSet):
	queryset = Booking.objects.select_related('listing', 'payment').all().order_by('-created_at')
	serializer_class = BookingSerializer

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		booking = serializer.save()

		payment_data = None
		payment_error = None
		try:
			payment = self._initiate_payment(booking)
			payment_data = PaymentSerializer(payment).data
		except PaymentGatewayError as exc:
			payment_error = str(exc)
			logger.warning("Booking %s created but payment initiation failed: %s", booking.id, exc)

		response_payload = BookingSerializer(booking).data
		response_payload['payment'] = payment_data
		if payment_error:
			response_payload['payment_error'] = payment_error

		headers = self.get_success_headers(response_payload)
		return Response(response_payload, status=status.HTTP_201_CREATED, headers=headers)

	@action(detail=True, methods=['post'], url_path='initiate-payment')
	def initiate_payment(self, request, pk=None):
		booking = self.get_object()
		try:
			payment = self._initiate_payment(booking)
		except PaymentGatewayError as exc:
			return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		return Response(
			{
				'checkout_url': payment.checkout_url,
				'reference': payment.reference,
				'status': payment.status,
				'booking': booking.id,
			}
		)

	@action(detail=True, methods=['post'], url_path='verify-payment')
	def verify_payment(self, request, pk=None):
		booking = self.get_object()
		try:
			payment = booking.payment
		except Payment.DoesNotExist:
			return Response({'detail': 'No payment record found for this booking.'}, status=status.HTTP_404_NOT_FOUND)

		try:
			payment = self._verify_payment(payment)
		except PaymentGatewayError as exc:
			return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		return Response(PaymentSerializer(payment).data)

	def _initiate_payment(self, booking: Booking) -> Payment:
		secret_key = getattr(settings, 'CHAPA_SECRET_KEY', None)
		if not secret_key:
			raise PaymentGatewayError('Chapa secret key is not configured. Set CHAPA_SECRET_KEY in the environment.')

		base_url = getattr(settings, 'CHAPA_BASE_URL', 'https://api.chapa.co/v1').rstrip('/')
		init_url = f"{base_url}/transaction/initialize"
		callback_url = getattr(settings, 'CHAPA_CALLBACK_URL', '')
		return_url = getattr(settings, 'CHAPA_RETURN_URL', '')

		payment, created = Payment.objects.get_or_create(
			booking=booking,
			defaults={
				'reference': self._generate_reference(booking),
				'amount': booking.total_price,
				'currency': 'ETB',
			},
		)

		if not created and payment.is_settled:
			raise PaymentGatewayError('Payment has already been completed for this booking.')

		if not created and payment.status != Payment.STATUS_PENDING:
			payment.reference = self._generate_reference(booking)

		payment.amount = booking.total_price
		payment.status = Payment.STATUS_PENDING
		payment.save(update_fields=['reference', 'amount', 'status', 'updated_at'])

		payload = {
			'amount': str(payment.amount),
			'currency': payment.currency,
			'email': booking.user_email,
			'first_name': booking.user_name.split(' ', 1)[0],
			'last_name': booking.user_name.split(' ', 1)[1] if ' ' in booking.user_name else booking.user_name,
			'tx_ref': payment.reference,
			'callback_url': callback_url,
			'return_url': return_url,
			'customization': {
				'title': 'ALX Travel Booking Payment',
				'description': f'Payment for booking #{booking.id} ({booking.listing.title})',
			},
		}

		try:
			response = requests.post(
				init_url,
				json=payload,
				headers={'Authorization': f'Bearer {secret_key}'},
				timeout=30,
			)
			response.raise_for_status()
			response_data = response.json()
		except requests.RequestException as exc:
			logger.exception('Failed to initiate payment with Chapa: %s', exc)
			raise PaymentGatewayError('Unable to reach Chapa to start the payment. Please retry.')
		except ValueError as exc:
			logger.exception('Chapa initialize response JSON decode error: %s', exc)
			raise PaymentGatewayError('Received an invalid response from Chapa.')

		if response_data.get('status') != 'success':
			payment.status = Payment.STATUS_FAILED
			payment.raw_response = response_data
			payment.save(update_fields=['status', 'raw_response', 'updated_at'])
			raise PaymentGatewayError(response_data.get('message', 'Chapa rejected the payment request.'))

		data = response_data.get('data', {})
		payment.checkout_url = data.get('checkout_url', '')
		payment.chapa_transaction_id = data.get('reference', '')
		payment.raw_response = response_data
		payment.save(update_fields=['checkout_url', 'chapa_transaction_id', 'raw_response', 'updated_at'])

		return payment

	@classmethod
	def _verify_payment(cls, payment: Payment) -> Payment:
		if payment.is_settled:
			return payment

		secret_key = getattr(settings, 'CHAPA_SECRET_KEY', None)
		if not secret_key:
			raise PaymentGatewayError('Chapa secret key is not configured. Set CHAPA_SECRET_KEY in the environment.')

		base_url = getattr(settings, 'CHAPA_BASE_URL', 'https://api.chapa.co/v1').rstrip('/')
		verify_url = f"{base_url}/transaction/verify/{payment.reference}"

		try:
			response = requests.get(verify_url, headers={'Authorization': f'Bearer {secret_key}'}, timeout=30)
			response.raise_for_status()
			response_data = response.json()
		except requests.RequestException as exc:
			logger.exception('Failed to verify payment %s: %s', payment.reference, exc)
			raise PaymentGatewayError('Unable to verify payment at this time. Please retry shortly.')
		except ValueError as exc:
			logger.exception('Chapa verify response JSON decode error: %s', exc)
			raise PaymentGatewayError('Received an invalid verification response from Chapa.')

		if response_data.get('status') != 'success':
			raise PaymentGatewayError(response_data.get('message', 'Unable to verify the payment with Chapa.'))

		data = response_data.get('data', {})
		chapa_status = data.get('status', '').lower()
		if chapa_status == 'success':
			payment.status = Payment.STATUS_COMPLETED
			payment.chapa_transaction_id = data.get('reference', payment.chapa_transaction_id)
			payment.raw_response = response_data
			payment.save(update_fields=['status', 'chapa_transaction_id', 'raw_response', 'updated_at'])
			cls._trigger_confirmation_email(payment.booking_id)
		elif chapa_status == 'pending':
			payment.status = Payment.STATUS_PENDING
			payment.raw_response = response_data
			payment.save(update_fields=['status', 'raw_response', 'updated_at'])
		else:
			payment.status = Payment.STATUS_FAILED
			payment.raw_response = response_data
			payment.save(update_fields=['status', 'raw_response', 'updated_at'])
			raise PaymentGatewayError('Payment verification failed or payment was declined.')

		return payment

	@staticmethod
	def _generate_reference(booking: Booking) -> str:
		return f"booking-{booking.id}-{uuid.uuid4().hex[:10]}"

	@staticmethod
	def _trigger_confirmation_email(booking_id: int) -> None:
		try:
			send_payment_confirmation_email.delay(booking_id)
		except Exception as exc:  # Celery not running, fallback to sync task call
			logger.warning('Celery delay failed, sending payment email synchronously: %s', exc)
			send_payment_confirmation_email_sync(booking_id)


class ChapaCallbackView(APIView):
	"""Handle asynchronous callbacks from Chapa."""

	authentication_classes: list = []
	permission_classes: list = []

	def post(self, request, *args, **kwargs):
		reference = request.data.get('tx_ref') or request.data.get('reference')
		if not reference:
			return Response({'detail': 'Missing tx_ref.'}, status=status.HTTP_400_BAD_REQUEST)

		return self._handle_reference(reference)

	def get(self, request, *args, **kwargs):
		reference = request.query_params.get('tx_ref') or request.query_params.get('reference')
		if not reference:
			return Response({'detail': 'Missing tx_ref.'}, status=status.HTTP_400_BAD_REQUEST)

		return self._handle_reference(reference)

	@staticmethod
	def _handle_reference(reference: str) -> Response:
		try:
			payment = Payment.objects.get(reference=reference)
		except Payment.DoesNotExist:
			return Response({'detail': 'Unknown payment reference.'}, status=status.HTTP_404_NOT_FOUND)

		try:
			payment = BookingViewSet._verify_payment(payment)
		except PaymentGatewayError as exc:
			return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		return Response(
			{
				'detail': 'Payment processed.',
				'status': payment.status,
				'reference': payment.reference,
			}
		)
