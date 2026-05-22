from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import PerfilUsuario, Rol

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        rol_ciudadano = Rol.objects.get(codigo="ciudadano")
        PerfilUsuario.objects.create(user=user, rol=rol_ciudadano)
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
