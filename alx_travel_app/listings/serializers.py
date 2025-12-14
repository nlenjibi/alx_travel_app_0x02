from rest_framework import serializers
from .models import Listing, Booking, Payment


class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'booking',
            'reference',
            'chapa_transaction_id',
            'amount',
            'currency',
            'status',
            'checkout_url',
            'raw_response',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
