from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'text', 'created_at', 'is_active']
    list_filter = ['is_active']