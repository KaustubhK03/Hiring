from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import *
from .forms import *

CustomUser = get_user_model()

# Inline Profile model
class ProfileInline(admin.StackedInline):  # Use TabularInline for a compact view
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'

# Extend UserAdmin to include Profile
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

# Unregister default User admin and register the custom one
admin.site.register(CustomUser, CustomUserAdmin)

# Register Profile separately (optional)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'experience', 'ats_score')
    search_fields = ('user__username', 'phone')
    
    
admin.site.register(ResultData)
admin.site.register(SelectedOptionDatabase)
admin.site.register(QuesModel)
admin.site.register(EmailManager)
admin.site.register(AdminSetting)
admin.site.register(QuestionBank)
admin.site.register(TestCases)
admin.site.register(CodingResult)
@admin.register(AdminDashboardConfig)
class AdminDashboardConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "selected_model", "chart_type")
    form = AdminDashboardForm