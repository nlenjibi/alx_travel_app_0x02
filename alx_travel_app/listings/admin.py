from django.contrib import admin

from .models import Listing, Booking, Payment


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "price", "available_from", "available_to", "created_at")
    search_fields = ("title", "location")
    list_filter = ("location",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "user_name", "user_email", "status", "start_date", "end_date", "total_price")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("user_name", "user_email")
    autocomplete_fields = ("listing",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "booking", "amount", "currency", "status", "chapa_transaction_id", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("reference", "chapa_transaction_id", "booking__user_email")
    readonly_fields = ("created_at", "updated_at", "raw_response")
    autocomplete_fields = ("booking",)
