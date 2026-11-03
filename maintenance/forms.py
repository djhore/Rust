
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    UserProfile,
    MaintenanceRequest,
    RoleVerificationCode,
)
from PIL import Image, UnidentifiedImageError, ImageOps
from django.core.exceptions import ValidationError

from io import BytesIO
from django.core.files.base import ContentFile

class TenantRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)

    apartment_number = forms.CharField(
        max_length=50,
        required=False,
    )

    role_code = forms.CharField(
        max_length=30,
        strip=True,
        label="Role Verification Code",
        help_text="Enter the verification code provided to you.",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "apartment_number",
            "password1",
            "password2",
            "role_code",
        ]

    def clean_role_code(self):
        code = self.cleaned_data["role_code"].strip()

        verification_code = RoleVerificationCode.objects.filter(
            code=code,
            is_used=False,
        ).first()

        if verification_code is None:
            raise forms.ValidationError(
                "This verification code is invalid or no longer available."
            )

        return code

    def clean(self):
        cleaned_data = super().clean()

        role_code = cleaned_data.get("role_code")
        apartment_number = cleaned_data.get("apartment_number")

        if role_code:
            verification_code = RoleVerificationCode.objects.filter(
                code=role_code,
                is_used=False,
            ).first()

            if (
                verification_code
                and verification_code.role == "tenant"
                and not apartment_number
            ):
                self.add_error(
                    "apartment_number",
                    "Apartment number is required for tenants.",
                )

        return cleaned_data



class MaintenanceRequestForm(forms.ModelForm):
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
    MAX_IMAGE_PIXELS = 20_000_000  # 20 megapixels

    class Meta:
        model = MaintenanceRequest
        fields = [
            "problem_title",
            "category",
            "description",
            "image",
        ]

    
    def clean_image(self):
        image = self.cleaned_data.get("image")

        # An image is optional.
        if not image:
            return image

        max_size = 5 * 1024 * 1024  # 5 MB
        max_pixels = 20_000_000

        if image.size > max_size:
            raise ValidationError("The image must not exceed 5 MB.")

        allowed_formats = {
            "JPEG": ("JPEG", ".jpg"),
            "PNG": ("PNG", ".png"),
            "WEBP": ("WEBP", ".webp"),
        }

        try:
            # Check that the uploaded file is a valid image.
            with Image.open(image) as original:
                image_format = original.format

                if image_format not in allowed_formats:
                    raise ValidationError(
                        "Upload a JPEG, PNG, or WEBP image."
                    )

                if original.width * original.height > max_pixels:
                    raise ValidationError(
                        "The image dimensions are too large."
                    )

                original.verify()

            # Reopen the image because verify() consumes its image data.
            image.seek(0)

            with Image.open(image) as original:
                cleaned_image = ImageOps.exif_transpose(original)
                cleaned_image.load()

                output = BytesIO()
                output_format, extension = allowed_formats[image_format]

                # JPEG does not support transparency.
                if output_format == "JPEG":
                    if cleaned_image.mode in ("RGBA", "LA", "P"):
                        cleaned_image = cleaned_image.convert("RGB")
                    elif cleaned_image.mode != "RGB":
                        cleaned_image = cleaned_image.convert("RGB")
                elif output_format == "PNG":
                    if cleaned_image.mode not in (
                        "RGB", "RGBA", "L", "LA", "P"
                    ):
                        cleaned_image = cleaned_image.convert("RGBA")
                elif output_format == "WEBP":
                    if cleaned_image.mode not in ("RGB", "RGBA"):
                        cleaned_image = cleaned_image.convert("RGBA")

                save_options = {"format": output_format}

                if output_format in ("JPEG", "WEBP"):
                    save_options["quality"] = 85
                    save_options["optimize"] = True
                elif output_format == "PNG":
                    save_options["optimize"] = True

                # Saving a fresh image removes the original metadata.
                cleaned_image.save(output, **save_options)

            if output.tell() > max_size:
                raise ValidationError(
                    "The processed image must not exceed 5 MB."
                )

            # Replace the original upload with the cleaned image.
            original_name = image.name.rsplit(".", 1)[0]
            image = ContentFile(
                output.getvalue(),
                name=original_name + extension,
            )

        except ValidationError:
            raise
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ):
            raise ValidationError(
                "Upload a valid JPEG, PNG, or WEBP image."
            )

        return image

class ProfileUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "apartment_number",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user = self.instance.user

        self.fields["username"].initial = user.username
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

        if self.instance.role != "tenant":
            self.fields.pop("apartment_number", None)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if (
            User.objects.filter(username=username)
            .exclude(pk=self.instance.user.pk)
            .exists()
        ):
            raise forms.ValidationError(
                "This username is already in use."
            )

        return username

class AssignTechnicianForm(forms.Form):
    technician = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label="Select a technician",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["technician"].queryset = User.objects.filter(
            is_active=True,
            userprofile__role="technician",
        ).order_by("username")


class ChangePriorityForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["priority"]
        labels = {
            "priority": "Request Priority",
        }
        widgets = {
            "priority": forms.Select(
                attrs={"class": "form-control"}
            ),
        }
