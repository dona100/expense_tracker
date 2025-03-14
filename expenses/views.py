from django.db import models  
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Expense
from .forms import ExpenseForm, RegisterForm
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'expenses/register.html', {'form': form})



@login_required(login_url='/login/')
def dashboard(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    
    # Filtering & Search
    category = request.GET.get('category', '')
    date_range = request.GET.get('date_range', '')
    query = request.GET.get('q', '')

    if category:
        expenses = expenses.filter(category=category)
    if date_range:
        expenses = expenses.filter(date__range=date_range.split(" - "))
    if query:
        expenses = expenses.filter(title__icontains=query)
    
    # Pagination
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Monthly Summary
    monthly_expenses = expenses.values('category').order_by().annotate(total=models.Sum('amount'))

    # Pie Chart
    categories = [x['category'] for x in monthly_expenses]
    amounts = [x['total'] for x in monthly_expenses]

    plt.figure(figsize=(5,5))
    plt.pie(amounts, labels=categories, autopct='%1.1f%%')
    plt.title('Expense Breakdown')

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_data = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()

    return render(request, 'expenses/dashboard.html', {
        'page_obj': page_obj,
        'total_expenses': sum(amounts),
        'chart': image_data
    })

@login_required(login_url='/login/')
def add_expense(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            return redirect('dashboard')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/expense_form.html', {'form': form})

@login_required(login_url='/login/')
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/expense_form.html', {'form': form})

@login_required(login_url='/login/')
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()
    return redirect('dashboard')

@login_required(login_url='/login/')
def export_csv(request):
    expenses = Expense.objects.filter(user=request.user)
    df = pd.DataFrame(expenses.values())
    response = df.to_csv(index=False)
    return response
