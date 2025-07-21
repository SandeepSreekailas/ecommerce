from django.shortcuts import render, redirect
from .models import Product, Order, Cart
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, ProfileUpdateForm
from django.contrib import messages
import stripe
from django.conf import settings
from django.urls import reverse
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

stripe.api_key = settings.STRIPE_SECRET_KEY


def home(request):
    return render(request, 'store/home.html')


def product_list(request):
    query = request.GET.get('q', '')  # Get search query from URL
    products = Product.objects.filter(name__icontains=query) if query else Product.objects.all()
    return render(request, 'store/product_list.html', {'products': products, 'query': query})


def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('product_list')
    else:
        form = AuthenticationForm()
    
    return render(request, 'store/login.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('product_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})


@login_required(login_url='login') 
def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1  # Increase quantity if product is already in cart
        cart_item.save()
    return redirect('cart_view')


@login_required(login_url='login') 
def cart_view(request):
    # cart_items = Cart.objects.filter(user=request.user)
    cart_items = list(Cart.objects.filter(user=request.user))
    for item in cart_items:
        item.total_price = item.quantity * item.product.price
    return render(request, 'store/cart.html', {'cart_items': cart_items})


def remove_from_cart(request, product_id):
    Cart.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect('cart_view')


def clear_cart(request):
    Cart.objects.filter(user=request.user).delete()
    return redirect('cart_view')


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')  
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'store/profile.html', {'form': form})


# @login_required
# def checkout(request):
#     # Check if single purchase is active
#     single_product_id = request.session.get("single_product_id")
#     if single_product_id:
#         product = get_object_or_404(Product, id=single_product_id)
#         cart_items = [{"product": product, "quantity": 1}]
#         single_purchase = True
#         product_ids = [product.id]
#     else:
#         cart_items = list(Cart.objects.filter(user=request.user))
#         single_purchase = False
#         product_ids = [item.product.id for item in cart_items]

#     if not cart_items:
#         return redirect('cart_view')

#     return render(request, 'store/checkout.html', {
#         'cart_items': cart_items,
#         'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
#         'single_purchase': single_purchase,
#         'product_ids_json': json.dumps(product_ids)
#     })


@login_required
def checkout(request):
    # ✅ Clear single product if not coming from buy now
    if not request.session.get("from_buy_now", False):
        request.session.pop("single_product_id", None)

    single_product_id = request.session.get("single_product_id")

    cart_items = []
    product_ids = []
    single_purchase = False
    grand_total = 0

    if single_product_id:
        product = get_object_or_404(Product, id=single_product_id)
        item = {
            "product": product,
            "quantity": 1,
            "total_price": product.price
        }
        cart_items = [item]
        product_ids = [product.id]
        single_purchase = True
        grand_total = product.price

    else:
        db_cart_items = list(Cart.objects.filter(user=request.user))
        for cart_item in db_cart_items:
            item_total = cart_item.quantity * cart_item.product.price
            cart_items.append({
                "product": cart_item.product,
                "quantity": cart_item.quantity,
                "total_price": item_total
            })
            grand_total += item_total
            product_ids.append(cart_item.product.id)

    if not cart_items:
        return redirect('cart_view')

    # ✅ Reset the buy now flag after use
    request.session["from_buy_now"] = False

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        'single_purchase': single_purchase,
        'product_ids_json': json.dumps(product_ids),
        'grand_total': grand_total
    })


@login_required
def checkout_single(request, product_id):
    request.session["single_product_id"] = product_id
    request.session["from_buy_now"] = True
    request.session.pop("full_cart_product_ids", None)
    return redirect("checkout")




# @login_required
# def create_stripe_checkout_session(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         address = data.get("address", "").strip()

#         if not address:
#             return JsonResponse({"error": "Shipping address is required."}, status=400)

#         single_purchase = data.get("single_purchase", False)
#         product_ids = data.get("product_ids", [])

#         line_items = []

#         if single_purchase and len(product_ids) == 1:
#             # ✅ Process single product purchase
#             product = get_object_or_404(Product, id=product_ids[0])
#             line_items.append({
#                 "price_data": {
#                     "currency": "usd",
#                     "product_data": {"name": product.name},
#                     "unit_amount": int(product.price * 100),
#                 },
#                 "quantity": 1,
#             })

#             # ✅ Store single product ID for removal after payment
#             request.session["single_product_id"] = product_ids[0]
#             request.session.pop("full_cart_product_ids", None)  # Prevent full cart deletion

#         else:
#             # ✅ Process full cart checkout
#             if not product_ids:
#                 return JsonResponse({"error": "No products selected for checkout."}, status=400)

#             for product_id in product_ids:
#                 product = get_object_or_404(Product, id=product_id)
#                 line_items.append({
#                     "price_data": {
#                         "currency": "usd",
#                         "product_data": {"name": product.name},
#                         "unit_amount": int(product.price * 100),
#                     },
#                     "quantity": 1,
#                 })

#             request.session["full_cart_product_ids"] = product_ids
#             request.session.pop("single_product_id", None)  # Prevent single product deletion

#         try:
#             checkout_session = stripe.checkout.Session.create(
#                 payment_method_types=["card"],
#                 line_items=line_items,
#                 mode="payment",
#                 success_url=request.build_absolute_uri(reverse("payment_success")),
#                 cancel_url=request.build_absolute_uri(reverse("checkout")),
#             )

#             return JsonResponse({"url": checkout_session.url})

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)


@login_required
def create_stripe_checkout_session(request):
    if request.method == "POST":
        data = json.loads(request.body)
        address = data.get("address", "").strip()

        if not address:
            return JsonResponse({"error": "Shipping address is required."}, status=400)

        single_purchase = data.get("single_purchase", False)
        product_ids = data.get("product_ids", [])

        line_items = []

        if single_purchase and len(product_ids) == 1:
            product = get_object_or_404(Product, id=product_ids[0])
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": product.name},
                    "unit_amount": int(product.price * 100),
                },
                "quantity": 1,
            })

            request.session["single_product_id"] = product_ids[0]
            request.session.pop("full_cart_product_ids", None)

        else:
            if not product_ids:
                return JsonResponse({"error": "No products selected for checkout."}, status=400)

            cart_items = Cart.objects.filter(user=request.user, product_id__in=product_ids)

            for item in cart_items:
                line_items.append({
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": item.product.name},
                        "unit_amount": int(item.product.price * 100),
                    },
                    "quantity": item.quantity,
                })

            request.session["full_cart_product_ids"] = product_ids
            request.session.pop("single_product_id", None)

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=request.build_absolute_uri(reverse("payment_success")),
                cancel_url=request.build_absolute_uri(reverse("checkout")),
            )
            return JsonResponse({"url": checkout_session.url})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



@login_required
def payment_success(request):
    if request.session.get("single_product_id"):
        Cart.objects.filter(user=request.user, product_id=request.session.pop("single_product_id")).delete()
    elif request.session.get("full_cart_product_ids"):
        Cart.objects.filter(user=request.user, product_id__in=request.session.pop("full_cart_product_ids")).delete()

    return redirect("product_list")

