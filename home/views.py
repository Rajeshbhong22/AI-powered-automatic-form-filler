from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError

from home.models import DomicileApplication
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import DomicileApplication
from django.shortcuts import get_object_or_404
from .models import DomicileApplication
from .utils import generate_domicile_pdf
from django.contrib.auth.decorators import login_required
from .utils import extract_text_from_file, extract_entities


def registerpage(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already registered")
            return redirect('register')

        User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        messages.success(request, "Account created successfully")
        return redirect('login')

    return render(request, 'register.html')


def loginpage(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')

        messages.error(request, "Invalid email or password")
        return redirect('login')

    return render(request, 'login.html')


@login_required(login_url='login')
def dashboard(request):
    applications = DomicileApplication.objects.filter(user=request.user)
    return render(request, 'dashboard.html', {
        'applications': applications
    })

@login_required
def domicile(request):
    if request.method == "POST":
        extracted_data = {}

        for file in request.FILES.values():
            text = extract_text_from_file(file)
            entities = extract_entities(text)
            extracted_data.update(entities)

        # session me store
        request.session["ocr_data"] = extracted_data

        return redirect("domicile_form")

    return render(request, "domicile.html")

@login_required
def domicile(request):
    if request.method == "POST":
        extracted_data = {}

        for file in request.FILES.values():
            text = extract_text_from_file(file)
            entities = extract_entities(text)
            extracted_data.update(entities)

        # session me store
        request.session["ocr_data"] = extracted_data

        return redirect("domicile_form")

    return render(request, "domicile.html")


@login_required
def domicile_form(request):
    ocr_data = request.session.get("ocr_data", {})

    if request.method == 'POST':
        DomicileApplication.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            dob=request.POST['dob'],
            mobile=request.POST['mobile'],
            aadhaar=request.POST['aadhaar'],
            address=request.POST['address'],
            district=request.POST['district'],
            state=request.POST['state'],
            residence_years=request.POST['residence_years'],
            purpose=request.POST['purpose'],
        )
        request.session.pop("ocr_data", None)
        return redirect('dashboard')

    return render(request, 'domicile_form.html', {
        "ocr": ocr_data
    })


@login_required
def download_domicile_certificate(request, app_id):
    application = get_object_or_404(
        DomicileApplication,
        id=app_id,
        user=request.user,
        status='approved'
    )

    return generate_domicile_pdf(application)
def logout_user(request):
    logout(request)
    return redirect('login')


def home_redirect(request):
    return redirect('dashboard')
