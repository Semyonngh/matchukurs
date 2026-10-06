from django.db import models
from django.contrib.auth.models import User

class ExpenseArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expense_articles'
        verbose_name = 'Статья расходов'
        verbose_name_plural = 'Статьи расходов'
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name

class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tags'
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name

class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    article = models.ForeignKey(ExpenseArticle, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    expense_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-expense_date']

    def __str__(self):
        return f'{self.expense_date} — {self.amount}₽ ({self.article.name})'

class ExpenseTag(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='expense_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='expense_tags')

    class Meta:
        db_table = 'expenses_tags'
        verbose_name = 'Связь расхода и тега'
        verbose_name_plural = 'Связи расходов и тегов'
        unique_together = ('expense', 'tag')

    def __str__(self):
        return f'{self.expense_id} — {self.tag.name}'