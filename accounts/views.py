from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib import messages
from .forms import UserCreationForm, UserUpdateForm
from .models import User


def login_view(request):
    """Custom login view"""
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            return redirect('notes:dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    
    # Create a simple form for the template
    from django import forms
    class LoginForm(forms.Form):
        email = forms.EmailField(
            widget=forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'required': True
            })
        )
        password = forms.CharField(
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your password',
                'required': True
            })
        )
    
    form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


class SignUpView(SuccessMessageMixin, CreateView):
    """User registration view"""
    model = User
    form_class = UserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')
    success_message = 'Account created successfully! Please log in.'


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """User profile update view"""
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Profile updated successfully!'
    
    def get_object(self):
        return self.request.user
