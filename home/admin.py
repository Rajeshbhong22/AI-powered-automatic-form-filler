from django.contrib import admin
from .models import DomicileApplication
import uuid
@admin.register(DomicileApplication)
class DomicileApplicationAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'full_name',
        'user',
        'district',
        'purpose',
        'status',
        'submitted_at'
    )

    list_filter = ('status', 'purpose', 'state')
    search_fields = ('full_name', 'aadhaar', 'mobile')
    ordering = ('-submitted_at',)

    actions = ['approve_application', 'reject_application']

    def approve_application(self, request, queryset):
        for app in queryset:
            app.status = 'approved'
            app.certificate_no = f"DOM-{uuid.uuid4().hex[:8].upper()}"
            app.save()

        self.message_user(request, "Selected applications approved")

    approve_application.short_description = "Approve & Generate Certificate"
    @admin.action(description="Reject selected applications")
    def reject_application(self, request, queryset):
        queryset.update(status='rejected')
