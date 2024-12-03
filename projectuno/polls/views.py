from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView
from .models import Question, Choice, UserVote
from .forms import QuestionForm, ChoiceFormSet, UserRegistrationForm

class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """Return the published questions."""
        return Question.objects.filter(
            pub_date__lte=timezone.localtime()
        ).order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            voted_questions = Question.objects.filter(
                uservote__user=self.request.user
            ).values_list('id', flat=True)
            context['unvoted_questions'] = Question.objects.filter(
                pub_date__lte=timezone.localtime()
            ).exclude(id__in=voted_questions).order_by('-pub_date')
        return context

class UserLoginView(LoginView):
    template_name = 'polls/user_login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('polls:index')

class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'
    login_url = 'polls:user_login'

    def get_queryset(self):
        """Excludes any questions that aren't published yet."""
        return Question.objects.filter(pub_date__lte=timezone.localtime())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['has_voted'] = UserVote.objects.filter(
                user=self.request.user,
                question=self.object
            ).exists()
        return context

class CreateQuestionView(LoginRequiredMixin, generic.CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'polls/question_form.html'
    success_url = reverse_lazy('polls:index')
    login_url = 'polls:user_login'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['choices'] = ChoiceFormSet(self.request.POST)
        else:
            data['choices'] = ChoiceFormSet()
        return data
    
    def form_valid(self, form):
        context = self.get_context_data()
        choices = context['choices']
        self.object = form.save()
        if choices.is_valid():
            choices.instance = self.object
            choices.save()
        return super().form_valid(form)

class EditQuestionView(LoginRequiredMixin, generic.UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'polls/question_form.html'
    success_url = reverse_lazy('polls:index')
    login_url = 'polls:user_login'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['choices'] = ChoiceFormSet(self.request.POST, instance=self.object)
        else:
            data['choices'] = ChoiceFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        choices = context['choices']
        self.object = form.save()
        if choices.is_valid():
            choices.instance = self.object
            choices.save()
        return super().form_valid(form)

class RegisterView(CreateView):
    template_name = 'polls/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('polls:index')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Log the user in after registration
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        user = authenticate(username=username, password=password)
        login(self.request, user)
        messages.success(self.request, 'Registration successful! You can now vote on polls.')
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

@login_required(login_url='polls:user_login')
def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    
    # Check if user has already voted
    if UserVote.objects.filter(user=request.user, question=question).exists():
        messages.error(request, "You've already voted on this question!")
        return HttpResponseRedirect(reverse('polls:detail', args=(question.id,)))
    
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        UserVote.objects.create(
            user=request.user,
            question=question,
            choice=selected_choice
        )
        messages.success(request, 'Your vote was successfully recorded!')
        
        # Find next unvoted question
        next_question = Question.objects.filter(
            pub_date__lte=timezone.localtime()
        ).exclude(
            uservote__user=request.user
        ).order_by('-pub_date').first()
        
        if next_question:
            return HttpResponseRedirect(reverse('polls:detail', args=(next_question.id,)))
        return HttpResponseRedirect(reverse('polls:index'))
