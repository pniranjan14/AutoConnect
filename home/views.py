import json
import math
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from .models import *


def index(request):
    return render(request, "index.html")



@csrf_exempt
def register_user(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        username = request.POST.get("username") or full_name.replace(" ", "").lower()
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("login_register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("login_register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("login_register")

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name,
            role = 'user'
        )
        user.save()

        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login_register")

    return redirect("login_register")



@csrf_exempt
def register_provider(request):
    if request.method == "POST":
        full_name = request.POST.get("owner_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("login_register")


        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("login_register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("login_register")


        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name,
            role="provider", 
        )
        user.save()

        messages.success(request, "Provider account created successfully. Please log in.")
        return redirect("login_register")

    return redirect("login_register")


@login_required
def user_dashboard(request):
    # Get active services (pending bookings)
    active_services = Booking.objects.filter(user=request.user, status='Pending')

    # Get nearby providers (approved centers)
    nearby_providers = ServiceCenter.objects.filter(status='Approved')[:5]  # Limit to 5 for display

    # Calculate total savings (this could be based on completed bookings vs estimated prices)
    completed_bookings = Booking.objects.filter(user=request.user, status='Completed')
    total_savings = sum([b.price for b in completed_bookings if hasattr(b, 'price') and b.price]) or 0

    # Get average rating from user's reviews
    avg_rating = Review.objects.filter(user=request.user).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

    # Get recent bookings (last 3 completed)
    recent_bookings = Booking.objects.filter(user=request.user, status='Completed').order_by('-booking_time')[:3]

    # Add review count and avg rating to nearby providers
    for center in nearby_providers:
        reviews = Review.objects.filter(center=center)
        center.avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        center.review_count = reviews.count()

    return render(request, 'user_dashboard.html', {
        'user': request.user,
        'active_services': active_services,
        'nearby_providers': nearby_providers,
        'total_savings': total_savings,
        'avg_rating': avg_rating,
        'recent_bookings': recent_bookings,
    })

@login_required
def provider_dashboard(request):
    try:
        center = ServiceCenter.objects.get(user=request.user)
        from datetime import datetime, timedelta

        conversion_rate = 82.0

        # Today's bookings
        today = datetime.now().date()
        todays_bookings = Booking.objects.filter(center=center, booking_time__date=today).count()

        # Monthly revenue (sum of prices for completed bookings in current month)
        current_month = datetime.now().month
        current_year = datetime.now().year
        monthly_revenue = Booking.objects.filter(
            center=center,
            status='Completed',
            booking_time__month=current_month,
            booking_time__year=current_year
        ).aggregate(total=Sum('price'))['total'] or 0
        monthly_revenue_inr = float(monthly_revenue) * conversion_rate

        # Customer rating
        avg_rating = Review.objects.filter(center=center).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

        # Completed jobs
        completed_bookings = Booking.objects.filter(center=center, status='Completed').count()

        # Today's schedule (upcoming bookings, limit to 4)
        todays_schedule = Booking.objects.filter(
            center=center,
            booking_time__date__gte=today
        ).order_by('booking_time')[:4]

        # Add INR price to each booking
        for booking in todays_schedule:
            booking.price_inr = float(booking.price) * conversion_rate

        # Recent reviews (last 3)
        recent_reviews = Review.objects.filter(center=center).order_by('-review_date')[:3]

        # Weekly earnings (last 7 days, daily sums)
        week_ago = today - timedelta(days=6)
        weekly_earnings = []
        for i in range(7):
            day = week_ago + timedelta(days=i)
            daily_sum = Booking.objects.filter(
                center=center,
                status='Completed',
                booking_time__date=day
            ).aggregate(total=Sum('price'))['total'] or 0
            weekly_earnings.append(float(daily_sum) * conversion_rate)

        total_weekly_inr = sum(weekly_earnings)
        max_earning = max(weekly_earnings) if weekly_earnings else 1
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        return render(request, 'provider_dashboard.html', {
            'center': center,
            'todays_bookings': todays_bookings,
            'monthly_revenue_inr': monthly_revenue_inr,
            'avg_rating': avg_rating,
            'completed_bookings': completed_bookings,
            'todays_schedule': todays_schedule,
            'recent_reviews': recent_reviews,
            'weekly_earnings': weekly_earnings,
            'total_weekly_inr': total_weekly_inr,
            'max_earning': max_earning,
            'days': days,
        })
    except ServiceCenter.DoesNotExist:
        messages.error(request, "You need to create your service center first.")
        return redirect('home')

@login_required
def services_provided(request):
    try:
        center = ServiceCenter.objects.get(user=request.user)
        if request.method == 'POST':
            action = request.POST.get('action')
            service_id = request.POST.get('service_id')
            if action == 'update_price':
                price = request.POST.get('price')
                if price:
                    service_price, created = ServicePrice.objects.get_or_create(center=center, service_id=service_id)
                    service_price.price = price
                    service_price.save()
                    messages.success(request, 'Service price updated successfully.')
            elif action == 'update_name':
                service_name = request.POST.get('service_name')
                service_description = request.POST.get('service_description')
                if service_name:
                    service = Service.objects.get(id=service_id)
                    service.name = service_name
                    service.description = service_description or ''
                    service.save()
                    messages.success(request, 'Service details updated successfully.')
            elif action == 'remove':
                ServicePrice.objects.filter(center=center, service_id=service_id).delete()
                messages.success(request, 'Service removed successfully.')
            elif action == 'add':
                service_name = request.POST.get('service_name')
                service_description = request.POST.get('service_description')
                price = request.POST.get('price')
                if service_name and price:
                    # Create or get the service
                    service, created = Service.objects.get_or_create(
                        name=service_name,
                        defaults={'description': service_description or ''}
                    )
                    if not created and service_description:
                        service.description = service_description
                        service.save()

                    # Check if service price already exists
                    if not ServicePrice.objects.filter(center=center, service=service).exists():
                        ServicePrice.objects.create(center=center, service=service, price=price)
                        messages.success(request, 'Service added successfully.')
                    else:
                        messages.error(request, 'Service already exists for this center.')
                else:
                    messages.error(request, 'Service name and price are required.')
            return redirect('services_provided')
        service_prices = ServicePrice.objects.filter(center=center).select_related('service')
        all_services = Service.objects.all()
        conversion_rate = 82.0
        for sp in service_prices:
            sp.price_inr = float(sp.price) * conversion_rate
        return render(request, 'services_provided.html', {
            'center': center,
            'service_prices': service_prices,
            'all_services': all_services,
            'conversion_rate': conversion_rate
        })
    except ServiceCenter.DoesNotExist:
        return redirect('provider_dashboard')


def api_services(request, center_id):
    try:
        center = ServiceCenter.objects.get(id=center_id, status="Approved")
        service_prices = ServicePrice.objects.filter(center=center).select_related('service')
        services_data = []
        conversion_rate = 82.0  # Example conversion rate from USD to INR
        for sp in service_prices:
            price_inr = float(sp.price) * conversion_rate
            services_data.append({
                'id': sp.service.id,
                'name': sp.service.name,
                'price_usd': str(sp.price),
                'price_inr': f"₹{price_inr:.2f}"
            })
        return JsonResponse({'services': services_data})
    except ServiceCenter.DoesNotExist:
        return JsonResponse({'services': []})


@login_required
def emergency_assist(request):
    if request.method == "POST":
        emergency_type = request.POST.get("emergency_type")
        place_name = request.POST.get("place_name")
        center_id = request.POST.get("center_id")

        if not center_id:
            messages.error(request, "Please select a service center.")
            return redirect("emergency_assist")

        center = get_object_or_404(ServiceCenter, id=center_id, status="Approved")

        EmergencyRequest.objects.create(
            user=request.user,
            center=center,
            location=place_name,
            emergency_type=emergency_type,
            status="Pending"
        )

        messages.success(request, "Your emergency request has been submitted successfully.")
        return redirect("service_history")

    centers = ServiceCenter.objects.filter(status="Approved")
    return render(request, "emergency_assist.html", {"centers": centers})

@login_required
def admin_dashboard (request):
    return render(request, 'admin_dashboard.html')

@login_required
def find_workshop(request):
    centers = ServiceCenter.objects.filter(status='Approved')
    return render(request, 'find_workshop.html', {'centers': centers})

@login_required
def service_history(request):
    bookings = Booking.objects.filter(user=request.user)
    emergencies = EmergencyRequest.objects.filter(user=request.user)
    return render(request, 'service_history.html', {'bookings': bookings, 'emergencies': emergencies})

@login_required
def new_requests(request):
    center = ServiceCenter.objects.get(user=request.user)
    bookings = Booking.objects.filter(center=center, status='Pending')
    conversion_rate = 82.0
    for booking in bookings:
        booking.price_inr = float(booking.price) * conversion_rate
    return render(request, 'new_requests.html', {'bookings': bookings})

@login_required
def service_reports(request):
    center = ServiceCenter.objects.get(user=request.user)
    total_bookings = Booking.objects.filter(center=center).count()
    completed_bookings = Booking.objects.filter(center=center, status='Completed').count()
    avg_rating = Review.objects.filter(center=center).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    return render(request, 'service_reports.html', {
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'avg_rating': avg_rating
    })





def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, "Invalid username or password.")
            return redirect("login_register")

        login(request, user)

        if user.is_staff:
            return redirect("admin_dashboard")
        elif user.role == "provider":
            return redirect("provider_dashboard")
        elif user.role == 'user':
            return redirect("user_dashboard")
        else:
            return redirect("user_dashboard")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login_register")

@login_required
def user_reviews(request):
    if request.method == 'POST':
        center_id = request.POST.get('center_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        center = ServiceCenter.objects.get(id=center_id)
        Review.objects.create(user=request.user, center=center, rating=rating, comment=comment)
        messages.success(request, 'Review submitted successfully.')
        return redirect('user_reviews')
    
    centers = ServiceCenter.objects.filter(status='Approved')
    user_reviews = Review.objects.filter(user=request.user)
    return render(request, 'user_reviews.html', {'centers': centers, 'user_reviews': user_reviews})

@login_required
def user_profile(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_dashboard')
    return render(request, 'user_profile.html', {'user': user})


@login_required
def provider_profile(request):
    try:
        center = ServiceCenter.objects.get(user=request.user)
    except ServiceCenter.DoesNotExist:
        return redirect('provider_dashboard')

    return render(request, "provider_profile.html", {"center": center})


@login_required
def request_assistance(request):
    if request.method == "POST":
        center_id = request.POST.get("center_id")
        service_ids = request.POST.getlist("services")
        booking_date = request.POST.get("booking_date")

        if not center_id:
            messages.error(request, "Please select a service center.")
            return redirect("request_assistance")

        if not service_ids:
            messages.error(request, "Please select at least one service.")
            return redirect("request_assistance")

        center = get_object_or_404(ServiceCenter, id=center_id, status="Approved")

        # Create bookings for each selected service
        for service_id in service_ids:
            service_price = get_object_or_404(ServicePrice, center=center, service_id=service_id)
            Booking.objects.create(
                user=request.user,
                center=center,
                service_type=service_price.service.name,
                booking_time=booking_date,
                price=service_price.price
            )

        messages.success(request, f"Your booking for {len(service_ids)} service(s) has been submitted successfully.")
        return redirect("service_history")

    centers = ServiceCenter.objects.filter(status="Approved").prefetch_related('serviceprice_set__service')
    return render(request, "request_assistance.html", {"centers": centers})


def pending_centers(request):
    centers=ServiceCenter.objects.filter(status='Pending')
    return render(request, 'pending_centers.html', {'centers':centers})


def approve_service_center(request, center_id):
    center = get_object_or_404(ServiceCenter, id=center_id)
    center.status = "Approved"
    center.save()
    messages.success(request, f"Service Center '{center.center_name}' approved successfully.")
    return redirect("pending_centers")


def reject_service_center(request, center_id):
    center = get_object_or_404(ServiceCenter, id=center_id)
    center.status = "Rejected"
    center.save()
    messages.warning(request, f"Service Center '{center.center_name}' has been rejected.")
    return redirect("pending_centers")


def manage_users(request):
    users = User.objects.filter(is_staff=False)
    return render(request, 'manage_user.html', {'users': users})


def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.warning(request, f"User '{user.username}' has been blocked.")
    return redirect('manage_users')


def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, f"User '{user.username}' has been unblocked.")
    return redirect('manage_users')


def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.delete()
    messages.error(request, f"User '{username}' has been deleted.")
    return redirect('manage_users')



@login_required
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.center.user != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect("new_requests")

    if request.method == "POST":
        booking.status = "Booked"
        booking.save()
        messages.success(request, f"Booking #{booking.id} has been accepted.")
    return redirect("new_requests")

@login_required
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.center.user != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect("new_requests")

    if request.method == "POST":
        booking.status = "Cancelled"
        booking.save()
        messages.warning(request, f"Booking #{booking.id} has been rejected.")
    return redirect("new_requests")

@login_required
def provider_emergency(request):
    try:
        center = ServiceCenter.objects.get(user=request.user)
        emergencies = EmergencyRequest.objects.filter(center=center).order_by('-request_time')
        return render(request, 'provider_emergency.html', {
            'center': center,
            'emergencies': emergencies
        })
    except ServiceCenter.DoesNotExist:
        messages.error(request, "You need to create your service center first.")
        return redirect('provider_dashboard')

@login_required
def accept_emergency(request, emergency_id):
    emergency = get_object_or_404(EmergencyRequest, id=emergency_id)

    if emergency.center.user != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect("provider_emergency")

    if request.method == "POST":
        emergency.status = "Accepted"
        emergency.save()
        messages.success(request, f"Emergency request #{emergency.id} has been accepted.")
    return redirect("provider_emergency")

@login_required
def reject_emergency(request, emergency_id):
    emergency = get_object_or_404(EmergencyRequest, id=emergency_id)

    if emergency.center.user != request.user:
        messages.error(request, "Unauthorized action.")
        return redirect("provider_emergency")

    if request.method == "POST":
        emergency.status = "Rejected"
        emergency.save()
        messages.warning(request, f"Emergency request #{emergency.id} has been rejected.")
    return redirect("provider_emergency")


