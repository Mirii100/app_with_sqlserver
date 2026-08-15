from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.db.models import Sum
from .models import Chama, ChamaMembership

class ChamaMembershipInline(admin.TabularInline):
    model = ChamaMembership
    extra = 0
    fk_name = 'chama'
    readonly_fields = ('joined_at',)
    raw_id_fields = ('user',)
    verbose_name = 'Member'
    verbose_name_plural = 'Members'


@admin.register(Chama)
class ChamaAdmin(admin.ModelAdmin):
    change_list_template = 'admin/chamas/chama_changelist.html'
    list_display = (
        'id',
        'name',
        'admin',
        'member_count',
        'target_amount',
        'monthly_contribution',
        'contribution_frequency',
        'total_pool_balance',
        'status',
        'invite_code',
        'created_at',
    )
    list_filter = (
        'status',
        'contribution_frequency',
        'created_at',
    )
    search_fields = (
        'name',
        'description',
        'invite_code',
        'admin__username',
        'admin__email',
        'admin__phone_number',
    )
    readonly_fields = (
        'invite_code',
        'created_at',
        'updated_at',
    )
    list_select_related = ('admin',)
    ordering = ('-created_at',)
    list_per_page = 25
    inlines = (ChamaMembershipInline,)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('report/', self.admin_site.admin_view(self.report_view), name='chamas_report'),
        ]
        return custom + urls

    def report_view(self, request):
        chamas = Chama.objects.all()
        by_status = chamas.values('status').annotate(total=Sum('total_pool_balance'))
        
        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Chama Analytics',
            'by_status': list(by_status),
        })
        return render(request, 'admin/chamas/report.html', context)


@admin.register(ChamaMembership)
class ChamaMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'chama',
        'user',
        'role',
        'contributed_amount',
        'joined_at',
    )
    list_filter = (
        'chama',
        'role',
        'joined_at',
    )
    search_fields = (
        'chama__name',
        'chama__invite_code',
        'user__username',
        'user__email',
        'user__phone_number',
    )
    readonly_fields = ('joined_at',)
    list_select_related = ('chama', 'user')
    ordering = ('-joined_at',)
    list_per_page = 25
