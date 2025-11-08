from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.views.decorators.http import require_POST

# For registering new users
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect("/") #change this to redirect to /users/login after login page is built
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", { "form": form})

# For existing users to login
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form": form})

# Logout for logged in users
@require_POST
def logout_view(request):
    logout(request)
    return redirect("index")