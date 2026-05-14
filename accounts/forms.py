from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Profile


User = get_user_model()


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Tên đăng nhập hoặc email")

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            auth_username = username
            if "@" in username:
                user = User.objects.filter(email__iexact=username).first()
                if user:
                    auth_username = user.get_username()

            self.user_cache = authenticate(
                self.request,
                username=auth_username,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Tên đăng nhập/email hoặc mật khẩu không đúng.",
                    code="invalid_login",
                )
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RegisterForm(UserCreationForm):
    error_messages = {
        "password_mismatch": "Hai mật khẩu không khớp.",
    }

    full_name = forms.CharField(
        max_length=150,
        label="Họ và tên",
        error_messages={"required": "Vui lòng nhập họ và tên."},
    )
    email = forms.EmailField(
        label="Email",
        error_messages={
            "required": "Vui lòng nhập email.",
            "invalid": "Email không hợp lệ.",
        },
    )
    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        label="Vai trò",
        error_messages={
            "required": "Vui lòng chọn vai trò.",
            "invalid_choice": "Vai trò không hợp lệ.",
        },
    )
    terms = forms.BooleanField(
        required=True,
        label="Điều khoản",
        error_messages={"required": "Bạn cần xác nhận điều khoản trước khi đăng ký."},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "full_name",
            "email",
            "username",
            "role",
            "password1",
            "password2",
            "terms",
        )
        labels = {
            "username": "Tên đăng nhập",
            "password1": "Mật khẩu",
            "password2": "Xác nhận mật khẩu",
        }
        error_messages = {
            "username": {
                "required": "Vui lòng nhập tên đăng nhập.",
                "unique": "Tên đăng nhập này đã được sử dụng.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Tên đăng nhập"
        self.fields["username"].error_messages.update(
            {"required": "Vui lòng nhập tên đăng nhập."}
        )
        self.fields["password1"].label = "Mật khẩu"
        self.fields["password1"].error_messages.update(
            {"required": "Vui lòng nhập mật khẩu."}
        )
        self.fields["password2"].label = "Xác nhận mật khẩu"
        self.fields["password2"].error_messages.update(
            {"required": "Vui lòng xác nhận mật khẩu."}
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["full_name"]
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={"role": self.cleaned_data["role"]},
            )

        return user
