from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

MAX_PROFILE_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_PROFILE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def build_full_name(user) -> str:
    name = f"{user.first_name} {user.last_name}".strip()
    if name:
        return name
    local = user.email.split("@")[0] if user.email else ""
    return local or "User"


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ensures email is normalized and JWT fields stay aligned with USERNAME_FIELD (email)."""

    username_field = "email"

    def validate(self, attrs):
        field = self.username_field
        attrs[field] = User.objects.normalize_email(attrs[field])
        return super().validate(attrs)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    experience_level = serializers.ChoiceField(
        choices=User.ExperienceLevel.choices,
        required=False,
        allow_null=True,
    )
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        default=User.Role.STUDENT,
    )
    admin_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        # Keep password match check first so users get immediate, clear feedback.
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        selected_role = attrs.get("role", User.Role.STUDENT)
        if selected_role != User.Role.STUDENT:
            raise serializers.ValidationError(
                {"role": "Public registration is for student accounts only."}
            )

        if not attrs.get("experience_level"):
            raise serializers.ValidationError(
                {"experience_level": "Learning level is required for student accounts."}
            )

        # Django's built-in validators enforce strength and common-password rules.
        validate_password(attrs["password"], User(email=attrs["email"]))
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return User.objects.normalize_email(value)

    def create(self, validated_data):
        experience_level = validated_data.pop("experience_level", None)
        validated_data.pop("confirm_password", None)
        validated_data.pop("admin_code", None)
        validated_data.pop("role", None)
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Role.STUDENT,
            experience_level=experience_level,
        )


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "full_name",
            "experience_level",
            "profile_image_url",
            "created_at",
        )
        read_only_fields = fields

    def get_full_name(self, obj):
        return build_full_name(obj)

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get("request")
        url = obj.profile_image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class ProfileUpdateSerializer(serializers.ModelSerializer):
    remove_profile_image = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "experience_level",
            "profile_image",
            "remove_profile_image",
        )
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "experience_level": {"required": False, "allow_null": True},
            "profile_image": {"required": False, "allow_null": True},
        }

    def validate_profile_image(self, value):
        if value is None:
            return value
        content_type = getattr(value, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_PROFILE_IMAGE_TYPES:
            raise serializers.ValidationError("Upload a JPG, PNG, WebP, or GIF image.")
        if value.size > MAX_PROFILE_IMAGE_BYTES:
            raise serializers.ValidationError("Profile image must be 2 MB or smaller.")
        return value

    def validate(self, attrs):
        user = self.instance
        if (
            user.role == User.Role.STUDENT
            and "experience_level" in attrs
            and not attrs.get("experience_level")
        ):
            raise serializers.ValidationError(
                {"experience_level": "Learning level is required for student accounts."}
            )
        return attrs

    def update(self, instance, validated_data):
        remove_image = validated_data.pop("remove_profile_image", False)
        new_image = validated_data.get("profile_image")

        if remove_image and instance.profile_image:
            instance.profile_image.delete(save=False)
            instance.profile_image = None
            validated_data.pop("profile_image", None)
        elif new_image and instance.profile_image:
            instance.profile_image.delete(save=False)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
