from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Expense, CATEGORY_CHOICES
from .forms import ExpenseForm,RegisterForm
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

    
    category_choices = CATEGORY_CHOICES  

    # Filtering & Search
    category = request.GET.get('category', '')
    date_range = request.GET.get('date_range', '')
    query = request.GET.get('q', '')

    if category:
        expenses = expenses.filter(category=category)

    if date_range:
        try:
            start_date, end_date = date_range.split(" to ")
            expenses = expenses.filter(date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, "Invalid date range format. Use YYYY-MM-DD - YYYY-MM-DD")


    if query:
        expenses = expenses.filter(title__icontains=query)

    # Pagination 
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    #  Expense Summary 
    categorized_summary = (
        expenses.values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    
    categories = [item["category"] for item in categorized_summary]
    amounts = [item["total"] for item in categorized_summary]

    #  Pie Chart
    plt.figure(figsize=(5, 5))
    if amounts:
        plt.pie(amounts, labels=categories, autopct='%1.1f%%')
        plt.title("Expense Breakdown")
    else:
        plt.text(0.5, 0.5, "No Data", horizontalalignment="center", verticalalignment="center")

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_data = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()

    return render(request, "expenses/dashboard.html", {
        "page_obj": page_obj,
        "category_choices": category_choices,  
        "total_expenses": sum(amounts),
        "chart": image_data,
        "categorized_summary": categorized_summary,
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

    if request.method == "POST":
        expense.delete()
        return redirect('dashboard')  

    return render(request, 'expenses/delete_expense.html', {'expense': expense})

@login_required(login_url='/login/')
def export_csv(request):
    expenses = Expense.objects.filter(user=request.user)
    df = pd.DataFrame(expenses.values())

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    
    df.to_csv(path_or_buf=response, index=False)
    
    return response


