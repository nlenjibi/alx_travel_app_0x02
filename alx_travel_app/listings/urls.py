from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet, ChapaCallbackView

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('payments/chapa/callback/', ChapaCallbackView.as_view(), name='chapa-callback'),
]
