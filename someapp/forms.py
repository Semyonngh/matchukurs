from django.forms import ModelForm
from .models import ExpenseArticle, Tag, Expense

class ExpenseArticleForm(ModelForm):
    class Meta:
        model = ExpenseArticle
        fields = ['name', 'description']


class TagForm(ModelForm):
    class Meta:
        model = Tag
        fields = ['name']

class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['article', 'amount', 'description', 'expense_date']