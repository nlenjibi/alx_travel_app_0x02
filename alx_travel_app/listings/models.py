from django.db import models


class Listing(models.Model):
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	location = models.CharField(max_length=200)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	available_from = models.DateField(null=True, blank=True)
	available_to = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.title


class Booking(models.Model):
	STATUS_CHOICES = (
		("pending", "Pending"),
		("confirmed", "Confirmed"),
		("cancelled", "Cancelled"),
	)

	listing = models.ForeignKey(Listing, related_name="bookings", on_delete=models.CASCADE)
	user_name = models.CharField(max_length=150)
	user_email = models.EmailField()
	start_date = models.DateField()
	end_date = models.DateField()
	total_price = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Booking #{self.id} for {self.listing.title}"


class Payment(models.Model):
	STATUS_PENDING = "pending"
	STATUS_COMPLETED = "completed"
	STATUS_FAILED = "failed"
	STATUS_EXPIRED = "expired"

	STATUS_CHOICES = (
		(STATUS_PENDING, "Pending"),
		(STATUS_COMPLETED, "Completed"),
		(STATUS_FAILED, "Failed"),
		(STATUS_EXPIRED, "Expired"),
	)

	booking = models.OneToOneField(Booking, related_name="payment", on_delete=models.CASCADE)
	reference = models.CharField(max_length=120, unique=True)
	chapa_transaction_id = models.CharField(max_length=120, blank=True)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	currency = models.CharField(max_length=3, default="ETB")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	checkout_url = models.URLField(blank=True)
	raw_response = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Payment {self.reference} ({self.status})"

	@property
	def is_settled(self):
		return self.status == self.STATUS_COMPLETED
