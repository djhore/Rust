from django import forms

from django.contrib.auth.forms import UserCreationForm

from django.contrib.auth.models import User

from .models import UserProfile, MaintenanceRequest, RoleVerificationCode


class TenantRegistrationForm(UserCreationForm):

    first_name = forms.CharField(max_length=150)

    last_name = forms.CharField(max_length=150)

    email = forms.EmailField()

    phone_number = forms.CharField(max_length=20)

    apartment_number = forms.CharField(
        max_length=50,
        required=False
    )

    role_code = forms.CharField(
        max_length=30,
        label="Role Verification Code",
        help_text="Enter the verification code provided to you."
    )

    def clean(self):
        cleaned_data = super().clean()

        role_code = cleaned_data.get('role_code')
        apartment_number = cleaned_data.get('apartment_number')

        if role_code:
            try:
                verification_code = RoleVerificationCode.objects.get(
                    code=role_code
                )

                if (
                    verification_code.role == 'tenant'
                    and not apartment_number
                ):
                    self.add_error(
                        'apartment_number',
                        'Apartment number is required for tenants.'
                    )

            except RoleVerificationCode.DoesNotExist:
                pass

        return cleaned_data

    class Meta:

        model = User

        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'apartment_number',
            'password1',
            'password2',
            'role_code',
        ]

    def clean_role_code(self):

        code = self.cleaned_data['role_code'].strip()

        try:
            verification_code = RoleVerificationCode.objects.get(
                code=code
            )
        except RoleVerificationCode.DoesNotExist:
            raise forms.ValidationError(
                "Invalid role verification code."
            )

        if verification_code.is_used:
            raise forms.ValidationError(
                "This role verification code has already been used."
            )

        return code


class MaintenanceRequestForm(forms.ModelForm):

    class Meta:

        model = MaintenanceRequest

        fields = [
            'problem_title',
            'category',
            'description',
            'image',
        ]

class ProfileUpdateForm(forms.ModelForm):

    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'apartment_number',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        user = self.instance.user

        self.fields['username'].initial = user.username
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

        if self.instance.role != 'tenant':
            self.fields.pop('apartment_number', None)

    def clean_username(self):

        username = self.cleaned_data['username'].strip()

        if User.objects.filter(
            username=username
        ).exclude(
            pk=self.instance.user.pk
        ).exists():

            raise forms.ValidationError(
                "This username is already in use."
            )

        return username

class AssignTechnicianForm(forms.ModelForm):

    class Meta:
        model = MaintenanceRequest
        fields = ['assigned_technician']
        labels = {
            'assigned_technician': 'Assign Technician',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['assigned_technician'].queryset = User.objects.filter(
            userprofile__role='technician',
            is_active=True
        )

        self.fields['assigned_technician'].empty_label = 'Select a technician'

class ChangePriorityForm(forms.ModelForm):

    class Meta:
        model = MaintenanceRequest
        fields = ['priority']
        labels = {
            'priority': 'Request Priority',
        }