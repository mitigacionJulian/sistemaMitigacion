from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import PerfilUsuario, Rol
from .phone import normalize_phone_co
from .serializers import PerfilSerializer

User = get_user_model()

ADMIN_ROLES = ("ciudadano", "autoridad", "analista", "administrador")


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ("id", "codigo", "nombre", "descripcion", "activo")


class UserAdminReadSerializer(serializers.ModelSerializer):
    perfil = PerfilSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "last_login",
            "perfil",
        )


class UserAdminCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    telefono = serializers.CharField(max_length=20, trim_whitespace=True, required=False, allow_blank=True)
    organizacion = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    rol_codigo = serializers.ChoiceField(choices=ADMIN_ROLES, default="ciudadano")
    is_active = serializers.BooleanField(default=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate_telefono(self, value):
        if not value or not str(value).strip():
            return ""
        return normalize_phone_co(value)

    def validate_rol_codigo(self, value):
        if not Rol.objects.filter(codigo=value, activo=True).exists():
            raise serializers.ValidationError("Rol no disponible.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        rol_codigo = validated_data.pop("rol_codigo")
        telefono = validated_data.pop("telefono", "")
        organizacion = validated_data.pop("organizacion", "")
        is_active = validated_data.pop("is_active", True)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        user.is_active = is_active
        user.save(update_fields=["is_active"])
        rol = Rol.objects.get(codigo=rol_codigo)
        PerfilUsuario.objects.create(
            user=user,
            rol=rol,
            telefono=telefono or None,
            organizacion=organizacion or None,
        )
        return user


class UserAdminUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    organizacion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    rol_codigo = serializers.ChoiceField(choices=ADMIN_ROLES, required=False)
    is_active = serializers.BooleanField(required=False)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
    )

    def validate_telefono(self, value):
        if value is None:
            return None
        if not str(value).strip():
            return ""
        return normalize_phone_co(value)

    def validate_rol_codigo(self, value):
        if not Rol.objects.filter(codigo=value, activo=True).exists():
            raise serializers.ValidationError("Rol no disponible.")
        return value

    def validate_password(self, value):
        if not value:
            return value
        validate_password(value)
        return value

    def validate_is_active(self, value):
        user = self.context.get("target_user")
        actor = self.context.get("actor")
        if user and actor and user.pk == actor.pk and value is False:
            raise serializers.ValidationError("No puede deshabilitar su propia cuenta.")
        return value

    def update(self, instance, validated_data):
        perfil = getattr(instance, "perfil", None)
        if perfil is None:
            raise serializers.ValidationError("El usuario no tiene perfil asociado.")

        password = validated_data.pop("password", None)
        rol_codigo = validated_data.pop("rol_codigo", None)
        telefono = validated_data.pop("telefono", None)
        organizacion = validated_data.pop("organizacion", None)

        user_fields = []
        for field in ("email", "first_name", "last_name", "is_active"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
                user_fields.append(field)

        if user_fields:
            instance.save(update_fields=user_fields)

        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])

        perfil_fields = []
        if telefono is not None:
            perfil.telefono = telefono or None
            perfil_fields.append("telefono")
        if organizacion is not None:
            perfil.organizacion = organizacion or None
            perfil_fields.append("organizacion")
        if rol_codigo is not None:
            perfil.rol = Rol.objects.get(codigo=rol_codigo)
            perfil_fields.append("rol")

        if perfil_fields:
            perfil.save(update_fields=perfil_fields)

        return instance
