from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Question, Choice

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text']
    
    def save(self, commit=True):
        question = super().save(commit=False)
        question.pub_date = timezone.localtime()
        if commit:
            question.save()
        return question

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['choice_text']

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = False  # Ensure regular users can't access admin
        user.is_superuser = False  # Extra security measure
        if commit:
            user.save()
        return user

ChoiceFormSet = forms.inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    extra=3,
    can_delete=True,
    min_num=2,
    validate_min=True
)
