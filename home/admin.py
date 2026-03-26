from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
import uuid

from .models import DomicileApplication, IncomeCertificateApplication, UserProfile

# ─── Custom Admin Site Title ───────────────────────────────────────────────────
admin.site.site_header  = "Seva AI — Administration Portal"
admin.site.site_title   = "Seva AI Admin"
admin.site.index_title  = "Application Management Dashboard"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _status_badge(status):
    """Return an HTML colored badge for a given status string."""
    palette = {
        'pending':    ('#F59E0B', '#1a1200', '&#9679; Pending Review'),
        'processing': ('#3B82F6', '#001233', '&#9654; Under Processing'),
        'approved':   ('#10B981', '#001a10', '&#10003; Approved'),
        'rejected':   ('#EF4444', '#1a0000', '&#10007; Rejected'),
    }
    color, bg, label = palette.get(status, ('#9CA3AF', '#111', status))
    return format_html(
        '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
        'font-size:0.78rem;font-weight:700;white-space:nowrap;">{}</span>',
        color, bg, label
    )


def _cert_badge(cert_no):
    if cert_no:
        return format_html(
            '<code style="background:#1a1c30;color:#818cf8;padding:3px 8px;'
            'border-radius:6px;font-size:0.8rem;">{}</code>',
            cert_no
        )
    return format_html('<span style="color:#6B7280;font-size:0.78rem;">{}</span>', '—')


# ─── User Profile Admin ────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'preferred_language', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter   = ('preferred_language',)

    fieldsets = (
        ('Account', {
            'fields': ('user', 'preferred_language', 'phone')
        }),
    )


# ─── Domicile Application Admin ────────────────────────────────────────────────
@admin.register(DomicileApplication)
class DomicileApplicationAdmin(admin.ModelAdmin):

    # ── List View ──────────────────────────────────────────────────────────────
    list_display = (
        'application_id', 'full_name', 'user',
        'district', 'state', 'purpose',
        'colored_status', 'certificate_badge',
        'submitted_at',
    )
    list_display_links = ('application_id', 'full_name')
    list_filter  = ('status', 'purpose', 'state', 'submitted_at')
    search_fields = ('full_name', 'aadhaar', 'pan_number', 'mobile', 'voter_id', 'user__username')
    ordering      = ('-submitted_at',)
    date_hierarchy = 'submitted_at'
    list_per_page = 20

    actions = [
        'action_mark_processing',
        'action_approve',
        'action_reject',
    ]

    # ── Detail View Layout ─────────────────────────────────────────────────────
    save_on_top = True
    readonly_fields = (
        'application_id', 'submitted_at', 'reviewed_at', 'certificate_badge',
        'colored_status',
    )

    fieldsets = (
        ('Application Reference', {
            'fields': ('application_id', 'user', 'submitted_at'),
            'classes': ('wide',),
        }),
        ('Personal Information', {
            'fields': (
                ('full_name', 'father_name'),
                ('gender', 'dob'),
                'mobile',
            ),
            'classes': ('wide',),
        }),
        ('Identity Documents', {
            'fields': (
                ('aadhaar', 'pan_number'),
                'voter_id',
            ),
            'classes': ('wide',),
        }),
        ('Address Details', {
            'fields': (
                'address',
                ('district', 'state'),
                'residence_years',
                'purpose',
            ),
            'classes': ('wide',),
        }),
        ('Workflow: Status and Decision', {
            'fields': (
                'status',
                'review_notes',
                ('certificate_no', 'reviewed_at'),
                'colored_status',
                'certificate_badge',
            ),
            'classes': ('wide',),
        }),
    )

    # ── Custom Display Columns ─────────────────────────────────────────────────
    def application_id(self, obj):
        pk_str = str(obj.pk).zfill(4)
        return format_html(
            '<strong style="color:#818cf8;">DOM-{}</strong>', pk_str
        )
    application_id.short_description = 'App. ID'
    application_id.admin_order_field = 'pk'

    def colored_status(self, obj):
        return _status_badge(obj.status)
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def certificate_badge(self, obj):
        return _cert_badge(obj.certificate_no)
    certificate_badge.short_description = 'Certificate No.'

    # ── Bulk Actions ───────────────────────────────────────────────────────────
    @admin.action(description='[→] Mark as Under Processing')
    def action_mark_processing(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='processing')
        if updated:
            messages.success(request, f'{updated} application(s) moved to "Under Processing".')
        else:
            messages.warning(request, 'No pending applications selected.')

    @admin.action(description='[+] Approve & Generate Certificate Number')
    def action_approve(self, request, queryset):
        count = 0
        for app in queryset.exclude(status='approved'):
            app.status         = 'approved'
            app.certificate_no = f'DOM-{uuid.uuid4().hex[:8].upper()}'
            app.reviewed_at    = timezone.now()
            app.save(update_fields=['status', 'certificate_no', 'reviewed_at'])
            count += 1
        if count:
            messages.success(
                request,
                f'{count} domicile application(s) approved. '
                f'Certificate numbers have been generated.'
            )
        else:
            messages.warning(request, 'All selected applications are already approved.')

    @admin.action(description='[-] Reject Selected Applications')
    def action_reject(self, request, queryset):
        count = queryset.exclude(status='rejected').update(
            status='rejected',
            reviewed_at=timezone.now()
        )
        if count:
            messages.error(
                request,
                f'{count} application(s) rejected. '
                f'Remember to add rejection notes in each record.'
            )
        else:
            messages.warning(request, 'All selected applications are already rejected.')

    # ── Auto-fill reviewed_at on save ─────────────────────────────────────────
    def save_model(self, request, obj, form, change):
        if change and obj.status in ('approved', 'rejected') and not obj.reviewed_at:
            obj.reviewed_at = timezone.now()
        if obj.status == 'approved' and not obj.certificate_no:
            obj.certificate_no = f'DOM-{uuid.uuid4().hex[:8].upper()}'
        super().save_model(request, obj, form, change)

    # ── Changelist Summary Header ──────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        extra_context['summary'] = {
            'total':      qs.count(),
            'pending':    qs.filter(status='pending').count(),
            'processing': qs.filter(status='processing').count(),
            'approved':   qs.filter(status='approved').count(),
            'rejected':   qs.filter(status='rejected').count(),
        }
        return super().changelist_view(request, extra_context=extra_context)


# ─── Income Certificate Application Admin ─────────────────────────────────────
@admin.register(IncomeCertificateApplication)
class IncomeCertificateApplicationAdmin(admin.ModelAdmin):

    # ── List View ──────────────────────────────────────────────────────────────
    list_display = (
        'application_id', 'full_name', 'user',
        'annual_income_fmt', 'income_source',
        'district', 'state',
        'colored_status', 'certificate_badge',
        'submitted_at',
    )
    list_display_links = ('application_id', 'full_name')
    list_filter  = ('status', 'income_source', 'state', 'submitted_at')
    search_fields = ('full_name', 'aadhaar', 'pan_number', 'mobile', 'user__username')
    ordering      = ('-submitted_at',)
    date_hierarchy = 'submitted_at'
    list_per_page = 20

    actions = [
        'action_mark_processing',
        'action_approve',
        'action_reject',
    ]

    # ── Detail View Layout ─────────────────────────────────────────────────────
    save_on_top = True
    readonly_fields = (
        'application_id', 'submitted_at', 'reviewed_at',
        'certificate_badge', 'colored_status',
    )

    fieldsets = (
        ('Application Reference', {
            'fields': ('application_id', 'user', 'submitted_at'),
            'classes': ('wide',),
        }),
        ('Personal Information', {
            'fields': (
                ('full_name', 'father_name'),
                ('gender', 'dob'),
                'mobile',
            ),
            'classes': ('wide',),
        }),
        ('Identity Documents', {
            'fields': (
                ('aadhaar', 'pan_number'),
            ),
            'classes': ('wide',),
        }),
        ('Address Details', {
            'fields': (
                'address',
                ('district', 'state'),
            ),
            'classes': ('wide',),
        }),
        ('Income Details', {
            'fields': (
                ('annual_income', 'income_source'),
                'purpose',
            ),
            'classes': ('wide',),
        }),
        ('Workflow — Status & Decision', {
            'fields': (
                'status',
                'review_notes',
                ('certificate_no', 'reviewed_at'),
                'colored_status',
                'certificate_badge',
            ),
            'classes': ('wide',),
            'description': (
                'Change status and save — OR use bulk actions. '
                'Fill "Review Notes" with the rejection reason before rejecting.'
            ),
        }),
    )

    # ── Custom Display Columns ─────────────────────────────────────────────────
    def application_id(self, obj):
        pk_str = str(obj.pk).zfill(4)
        return format_html(
            '<strong style="color:#6ee7b7;">INC-{}</strong>', pk_str
        )
    application_id.short_description = 'App. ID'
    application_id.admin_order_field = 'pk'

    def colored_status(self, obj):
        return _status_badge(obj.status)
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'

    def certificate_badge(self, obj):
        return _cert_badge(obj.certificate_no)
    certificate_badge.short_description = 'Certificate No.'

    def annual_income_fmt(self, obj):
        try:
            val = int(obj.annual_income)
            return format_html(
                '<span style="color:#6ee7b7;font-weight:600;">&#8377; {:,}</span>', val
            )
        except (ValueError, TypeError):
            return obj.annual_income
    annual_income_fmt.short_description = 'Annual Income'
    annual_income_fmt.admin_order_field = 'annual_income'

    # ── Bulk Actions ───────────────────────────────────────────────────────────
    @admin.action(description='[→] Mark as Under Processing')
    def action_mark_processing(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='processing')
        if updated:
            messages.success(request, f'{updated} application(s) moved to "Under Processing".')
        else:
            messages.warning(request, 'No pending applications selected.')

    @admin.action(description='[+] Approve & Generate Certificate Number')
    def action_approve(self, request, queryset):
        count = 0
        for app in queryset.exclude(status='approved'):
            app.status         = 'approved'
            app.certificate_no = f'INC-{uuid.uuid4().hex[:8].upper()}'
            app.reviewed_at    = timezone.now()
            app.save(update_fields=['status', 'certificate_no', 'reviewed_at'])
            count += 1
        if count:
            messages.success(
                request,
                f'{count} income certificate application(s) approved. '
                f'Certificate numbers generated.'
            )
        else:
            messages.warning(request, 'All selected applications are already approved.')

    @admin.action(description='[-] Reject Selected Applications')
    def action_reject(self, request, queryset):
        count = queryset.exclude(status='rejected').update(
            status='rejected',
            reviewed_at=timezone.now()
        )
        if count:
            messages.error(
                request,
                f'{count} application(s) rejected. '
                f'Add rejection notes inside each record.'
            )
        else:
            messages.warning(request, 'All selected applications are already rejected.')

    # ── Auto-fill reviewed_at on save ─────────────────────────────────────────
    def save_model(self, request, obj, form, change):
        if change and obj.status in ('approved', 'rejected') and not obj.reviewed_at:
            obj.reviewed_at = timezone.now()
        if obj.status == 'approved' and not obj.certificate_no:
            obj.certificate_no = f'INC-{uuid.uuid4().hex[:8].upper()}'
        super().save_model(request, obj, form, change)

    # ── Changelist Summary Header ──────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)
        extra_context['summary'] = {
            'total':      qs.count(),
            'pending':    qs.filter(status='pending').count(),
            'processing': qs.filter(status='processing').count(),
            'approved':   qs.filter(status='approved').count(),
            'rejected':   qs.filter(status='rejected').count(),
        }
        return super().changelist_view(request, extra_context=extra_context)
