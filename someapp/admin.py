from django.contrib import admin
from .models import ExpenseArticle, Tag, Expense, ExpenseTag

@admin.register(ExpenseArticle)
class ExpenseArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'article', 'expense_date', 'user')
    list_filter = ('article', 'expense_date')
    date_hierarchy = 'expense_date'

@admin.register(ExpenseTag)
class ExpenseTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'expense', 'tag')