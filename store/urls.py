from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),

    # 🛒 Shopping Cart URLs
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),

    # ✅ Order Placement
    # path('order/<int:product_id>/', views.place_order, name='place_order'),  # Single Product Order
    path('checkout/', views.checkout, name='checkout'),  # Full Cart Checkout
    path('checkout/<int:product_id>/', views.checkout_single, name='checkout_single'),  # Buy Now Option
    # path('place_order/', views.place_order, name='place_order'),  # Final Checkout Processing
    path('payment-success/', views.payment_success, name='payment_success'),  # Stripe Payment Success
    path('create-stripe-checkout-session/', views.create_stripe_checkout_session, name='create_stripe_checkout_session'),



    # 👤 Authentication & User Management
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
]
