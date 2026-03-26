import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import DomicileApplication, IncomeCertificateApplication, UserProfile
from .utils import (
    extract_text_from_file, extract_entities,
    generate_domicile_pdf, generate_income_pdf,
)


# ─── Auth Views ────────────────────────────────────────────────────────────────

def registerpage(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=email).exists():
            messages.error(request, "This email is already registered.")
            return redirect('register')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        UserProfile.objects.create(user=user)
        messages.success(request, "Account created! Please log in.")
        return redirect('login')

    return render(request, 'register.html')


def loginpage(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Invalid email or password. Please try again.")
        return redirect('login')

    return render(request, 'login.html')


def logout_user(request):
    logout(request)
    return redirect('login')


def home_redirect(request):
    return redirect('dashboard')


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def dashboard(request):
    domicile_apps = DomicileApplication.objects.filter(user=request.user).order_by('-submitted_at')
    income_apps = IncomeCertificateApplication.objects.filter(user=request.user).order_by('-submitted_at')

    dom_stats = {
        'total':      domicile_apps.count(),
        'pending':    domicile_apps.filter(status='pending').count(),
        'processing': domicile_apps.filter(status='processing').count(),
        'approved':   domicile_apps.filter(status='approved').count(),
        'rejected':   domicile_apps.filter(status='rejected').count(),
    }
    inc_stats = {
        'total':      income_apps.count(),
        'pending':    income_apps.filter(status='pending').count(),
        'processing': income_apps.filter(status='processing').count(),
        'approved':   income_apps.filter(status='approved').count(),
        'rejected':   income_apps.filter(status='rejected').count(),
    }

    return render(request, 'dashboard.html', {
        'domicile_apps': domicile_apps,
        'income_apps': income_apps,
        'dom_stats': dom_stats,
        'inc_stats': inc_stats,
    })


# ─── Domicile Certificate ──────────────────────────────────────────────────────

@login_required(login_url='login')
def domicile(request):
    """Upload page — shows doc upload form."""
    return render(request, 'domicile.html')


@login_required(login_url='login')
@require_POST
def domicile_ocr_ajax(request):
    """
    AJAX endpoint: receive uploaded files, run OCR, return extracted data as JSON.
    Frontend shows loading animation then redirects to the form page.
    """
    extracted_data = {}
    ocr_texts = []

    for key, file in request.FILES.items():
        try:
            text = extract_text_from_file(file)
            ocr_texts.append(text)
            entities = extract_entities(text)
            extracted_data.update(entities)
        except Exception as e:
            pass  # Silently skip failed files

    # Also try voice text if provided
    voice_text = request.POST.get('voice_text', '').strip()
    if voice_text:
        voice_entities = extract_entities(voice_text)
        extracted_data.update(voice_entities)

    request.session['ocr_data'] = extracted_data
    request.session['form_type'] = 'domicile'

    return JsonResponse({'status': 'success', 'extracted': extracted_data})


@login_required(login_url='login')
def domicile_form(request):
    """Review/edit form for domicile certificate."""
    ocr_data = request.session.get('ocr_data', {})

    if request.method == 'POST':
        try:
            DomicileApplication.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name', ''),
                father_name=request.POST.get('father_name', ''),
                gender=request.POST.get('gender', ''),
                dob=request.POST.get('dob', '2000-01-01'),
                mobile=request.POST.get('mobile', ''),
                aadhaar=request.POST.get('aadhaar', ''),
                pan_number=request.POST.get('pan_number', ''),
                voter_id=request.POST.get('voter_id', ''),
                address=request.POST.get('address', ''),
                district=request.POST.get('district', ''),
                state=request.POST.get('state', ''),
                residence_years=int(request.POST.get('residence_years', 0) or 0),
                purpose=request.POST.get('purpose', ''),
            )
            request.session.pop('ocr_data', None)
            messages.success(request, "Domicile application submitted successfully. Awaiting review.")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Submission error: {str(e)}")

    return render(request, 'domicile_form.html', {'ocr': ocr_data})


@login_required(login_url='login')
def download_domicile_certificate(request, app_id):
    application = get_object_or_404(
        DomicileApplication, id=app_id, user=request.user, status='approved'
    )
    return generate_domicile_pdf(application)


# ─── Income Certificate ────────────────────────────────────────────────────────

@login_required(login_url='login')
def income(request):
    """Upload page for income certificate."""
    return render(request, 'income.html')


@login_required(login_url='login')
@require_POST
def income_ocr_ajax(request):
    """AJAX OCR endpoint for income certificate."""
    extracted_data = {}

    for key, file in request.FILES.items():
        try:
            text = extract_text_from_file(file)
            entities = extract_entities(text)
            extracted_data.update(entities)
        except Exception:
            pass

    voice_text = request.POST.get('voice_text', '').strip()
    if voice_text:
        voice_entities = extract_entities(voice_text)
        extracted_data.update(voice_entities)

    request.session['ocr_data'] = extracted_data
    request.session['form_type'] = 'income'

    return JsonResponse({'status': 'success', 'extracted': extracted_data})


@login_required(login_url='login')
def income_form(request):
    """Review/edit form for income certificate."""
    ocr_data = request.session.get('ocr_data', {})

    if request.method == 'POST':
        try:
            IncomeCertificateApplication.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name', ''),
                father_name=request.POST.get('father_name', ''),
                gender=request.POST.get('gender', ''),
                dob=request.POST.get('dob', '2000-01-01'),
                mobile=request.POST.get('mobile', ''),
                aadhaar=request.POST.get('aadhaar', ''),
                pan_number=request.POST.get('pan_number', ''),
                address=request.POST.get('address', ''),
                district=request.POST.get('district', ''),
                state=request.POST.get('state', ''),
                annual_income=request.POST.get('annual_income', ''),
                income_source=request.POST.get('income_source', 'other'),
                purpose=request.POST.get('purpose', ''),
            )
            request.session.pop('ocr_data', None)
            messages.success(request, "Income certificate application submitted successfully. Awaiting review.")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Submission error: {str(e)}")

    return render(request, 'income_form.html', {'ocr': ocr_data})


@login_required(login_url='login')
def download_income_certificate(request, app_id):
    application = get_object_or_404(
        IncomeCertificateApplication, id=app_id, user=request.user, status='approved'
    )
    return generate_income_pdf(application)
