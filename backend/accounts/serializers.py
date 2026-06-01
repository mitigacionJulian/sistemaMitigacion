from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import PasswordResetToken, PerfilUsuario, Rol
from .phone import normalize_phone_co

User = get_user_model()

REGISTRO_ROLES = ("ciudadano", "analista")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    telefono = serializers.CharField(max_length=20, trim_whitespace=True)
    rol_codigo = serializers.ChoiceField(choices=REGISTRO_ROLES, default="ciudadano")

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate_telefono(self, value):
        return normalize_phone_co(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        rol_codigo = validated_data.pop("rol_codigo", "ciudadano")
        telefono_norm = validated_data.pop("telefono")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        rol = Rol.objects.get(codigo=rol_codigo)
        PerfilUsuario.objects.create(
            user=user,
            rol=rol,
            telefono=telefono_norm,
        )
        return user


class PerfilSerializer(serializers.ModelSerializer):
    rol_codigo = serializers.CharField(source="rol.codigo", read_only=True)
    rol_nombre = serializers.CharField(source="rol.nombre", read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = (
            "rol_codigo",
            "rol_nombre",
            "telefono",
            "organizacion",
            "acepta_notificaciones",
        )


class UserMeSerializer(serializers.ModelSerializer):
    perfil = PerfilSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "perfil",
        )


class PasswordResetRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    telefono = serializers.CharField(max_length=20, trim_whitespace=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        validate_password(attrs["password"])
        token = attrs["token"]
        try:
            row = PasswordResetToken.objects.select_related("user").get(
                token=token, used_at__isnull=True
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {"token": "Enlace inválido o ya utilizado."}
            ) from None
        if row.expires_at < timezone.now():
            raise serializers.ValidationError({"token": "El enlace expiró. Solicite uno nuevo."})
        attrs["reset_row"] = row
        return attrs

    def save(self, **kwargs):
        row = self.validated_data["reset_row"]
        user = row.user
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])
        row.used_at = timezone.now()
        row.save(update_fields=["used_at"])
        return user
