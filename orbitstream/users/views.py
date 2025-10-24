from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout

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

# For logged in users to logout
def logout_view(request):
    if request.method == "GET":
        logout(request)
        return redirect("/")