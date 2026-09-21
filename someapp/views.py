from datetime import date, timedelta
from json import loads

from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.dateparse import parse_date

from .models import ExpenseArticle, Tag, Expense, ExpenseTag
from .forms import ExpenseArticleForm, TagForm, ExpenseForm


def to_dict_article(a):
    return {
        'id': a.id,
        'user_id': a.user_id,
        'name': a.name,
        'description': a.description,
        'created_at': str(a.created_at),
    }


def to_dict_tag(t):
    return {
        'id': t.id,
        'user_id': t.user_id,
        'name': t.name,
        'created_at': str(t.created_at),
    }


def to_dict_expense(e):
    tags = Tag.objects.filter(expense_tags__expense=e)
    return {
        'id': e.id,
        'user_id': e.user_id,
        'amount': float(e.amount),
        'description': e.description,
        'expense_date': str(e.expense_date),
        'article': {'id': e.article.id, 'name': e.article.name},
        'tags': [to_dict_tag(t) for t in tags],
    }


def period_range(period, ref_date=None):
    ref_date = ref_date or date.today()
    if period == 'today':
        return ref_date, ref_date
    if period == 'week':
        return ref_date - timedelta(days=6), ref_date
    if period == 'month':
        return ref_date - timedelta(days=29), ref_date
    if period == 'year':
        return ref_date - timedelta(days=364), ref_date
    return None, None


def get_ref_date(request):
    raw = request.GET.get('date')
    if raw:
        parsed = parse_date(raw)
        if parsed:
            return parsed
    return date.today()


@method_decorator(csrf_exempt, name='dispatch')
class CategoryListView(View):
    def get(self, request):
        categories = ExpenseArticle.objects.all()
        data = [to_dict_article(a) for a in categories]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = ExpenseArticleForm(loads(request.body))
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return JsonResponse(to_dict_article(category), status=201)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class CategoryDetailView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        return JsonResponse(to_dict_article(c))

    def put(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        form = ExpenseArticleForm(loads(request.body), instance=c)
        if form.is_valid():
            form.save()
            return JsonResponse(to_dict_article(c))
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    def delete(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        c.delete()
        return JsonResponse({'status': 'ok'})


class CategoryExpensesView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=c)
        data = [to_dict_expense(e) for e in expenses]
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'category': to_dict_article(c),
            'count': len(data),
            'total': float(total),
            'data': data,
        })


class CategoryStatsView(View):
    def get(self, request, category_id):
        c = get_object_or_404(ExpenseArticle, id=category_id)
        expenses = Expense.objects.filter(article=c)
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'category': to_dict_article(c),
            'count': expenses.count(),
            'total': float(total),
        })


@method_decorator(csrf_exempt, name='dispatch')
class ExpenseListView(View):
    def get(self, request):
        expenses = Expense.objects.all()
        data = [to_dict_expense(e) for e in expenses]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        new_data = loads(request.body)
        tag_ids = new_data.pop('tag_ids', [])
        form = ExpenseForm(new_data)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            for tag_id in tag_ids:
                ExpenseTag.objects.create(expense=expense, tag_id=tag_id)
            return JsonResponse(to_dict_expense(expense), status=201)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ExpenseDetailView(View):
    def get(self, request, expense_id):
        e = get_object_or_404(Expense, id=expense_id)
        return JsonResponse(to_dict_expense(e))

    def put(self, request, expense_id):
        e = get_object_or_404(Expense, id=expense_id)
        new_data = loads(request.body)
        tag_ids = new_data.pop('tag_ids', None)
        form = ExpenseForm(new_data, instance=e)
        if form.is_valid():
            form.save()
            if tag_ids is not None:
                ExpenseTag.objects.filter(expense=e).delete()
                for tag_id in tag_ids:
                    ExpenseTag.objects.create(expense=e, tag_id=tag_id)
            return JsonResponse(to_dict_expense(e))
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    def delete(self, request, expense_id):
        e = get_object_or_404(Expense, id=expense_id)
        e.delete()
        return JsonResponse({'status': 'ok'})


@method_decorator(csrf_exempt, name='dispatch')
class TagListView(View):
    def get(self, request):
        tags = Tag.objects.all()
        data = [to_dict_tag(t) for t in tags]
        return JsonResponse({'count': len(data), 'data': data})

    def post(self, request):
        form = TagForm(loads(request.body))
        if form.is_valid():
            tag = form.save(commit=False)
            tag.user = request.user
            tag.save()
            return JsonResponse(to_dict_tag(tag), status=201)
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class TagDetailView(View):
    def get(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        return JsonResponse(to_dict_tag(t))

    def put(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        form = TagForm(loads(request.body), instance=t)
        if form.is_valid():
            form.save()
            return JsonResponse(to_dict_tag(t))
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    def delete(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        t.delete()
        return JsonResponse({'status': 'ok'})


class TagStatsView(View):
    def get(self, request, tag_id):
        t = get_object_or_404(Tag, id=tag_id)
        ids = ExpenseTag.objects.filter(tag=t).values_list('expense_id', flat=True)
        expenses = Expense.objects.filter(id__in=ids)
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'tag': to_dict_tag(t),
            'count': expenses.count(),
            'total': float(total),
        })


@method_decorator(csrf_exempt, name='dispatch')
class StatsPeriodView(View):
    def get(self, request, period):
        date_from, date_to = period_range(period, get_ref_date(request))
        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'period': period,
            'from': str(date_from),
            'to': str(date_to),
            'count': expenses.count(),
            'total': float(total),
        })


class StatsCustomPeriodView(View):
    def get(self, request):
        date_from = parse_date(request.GET.get('from', ''))
        date_to = parse_date(request.GET.get('to', ''))
        if not date_from or not date_to:
            return JsonResponse({'error': 'from и to обязательны'}, status=400)
        expenses = Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'period': 'custom',
            'from': str(date_from),
            'to': str(date_to),
            'count': expenses.count(),
            'total': float(total),
        })


class StatsTodayView(View):
    def get(self, request):
        today = date.today()
        expenses = Expense.objects.filter(expense_date=today)
        total = sum(e.amount for e in expenses)
        return JsonResponse({
            'period': 'today',
            'date': str(today),
            'count': expenses.count(),
            'total': float(total),
        })


class StatsByCategoryView(View):
    def get(self, request):
        date_from = parse_date(request.GET.get('from', ''))
        date_to = parse_date(request.GET.get('to', ''))
        if not date_from or not date_to:
            date_from, date_to = period_range('month', get_ref_date(request))

        expenses = Expense.objects.filter(
            expense_date__gte=date_from,
            expense_date__lte=date_to,
        )

        data = []
        for c in ExpenseArticle.objects.all():
            cat_expenses = expenses.filter(article=c)
            total = sum(e.amount for e in cat_expenses)
            data.append({
                'category_id': c.id,
                'name': c.name,
                'count': cat_expenses.count(),
                'total': float(total),
            })

        grand_total = sum(e.amount for e in expenses)

        return JsonResponse({
            'from': str(date_from),
            'to': str(date_to),
            'total': float(grand_total),
            'data': data,
        })