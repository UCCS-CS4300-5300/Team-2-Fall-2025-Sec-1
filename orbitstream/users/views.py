from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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

# User settings page
@login_required
def settings_view(request):
    if request.method == "POST":
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        password_form = PasswordChangeForm(request.user)

    return render(request, 'users/settings.html', {
        'password_form': password_form
    })