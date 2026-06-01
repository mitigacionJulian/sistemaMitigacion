import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .jwt_serializers import CustomTokenObtainPairSerializer
from .models import PasswordResetToken, PerfilUsuario
from .phone import build_whatsapp_url, normalize_phone_co
from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserMeSerializer,
)

User = get_user_model()


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class LoginTokenView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    payload = UserMeSerializer(user).data
    payload["tokens"] = _tokens_for_user(user)
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserMeSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    ser = PasswordResetRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    username = ser.validated_data["username"].strip()
    phone_input = ser.validated_data["telefono"]
    phone_norm = normalize_phone_co(phone_input)

    try:
        user = User.objects.select_related("perfil__rol").get(username__iexact=username)
    except User.DoesNotExist:
        return Response(
            {"detail": "No hay cuenta con ese usuario y celular registrado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    perfil = getattr(user, "perfil", None)
    if perfil is None or not perfil.telefono:
        return Response(
            {"detail": "El usuario no tiene celular registrado. Contacte al administrador."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    stored = perfil.telefono_normalizado
    if stored != phone_norm:
        return Response(
            {"detail": "El celular no coincide con el registrado en la cuenta."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ttl_hours = int(getattr(settings, "PASSWORD_RESET_TOKEN_HOURS", 1))
    token_plain = secrets.token_urlsafe(32)
    expires = timezone.now() + timedelta(hours=ttl_hours)
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    PasswordResetToken.objects.create(
        user=user,
        token=token_plain,
        expires_at=expires,
    )

    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend}/recuperar-clave?token={token_plain}"
    message = (
        f"Recuperación de contraseña — SG Mitigación Medellín.\n"
        f"Usuario: {user.username}\n"
        f"Enlace (válido {ttl_hours} h): {reset_url}"
    )
    whatsapp_url = build_whatsapp_url(phone_norm, message)

    return Response(
        {
            "detail": "Abra WhatsApp para enviarse el enlace de recuperación o use el enlace mostrado.",
            "whatsapp_url": whatsapp_url,
            "reset_url": reset_url,
            "expires_at": expires.isoformat(),
            "telefono": f"+{phone_norm}",
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    ser = PasswordResetConfirmSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response({"detail": "Contraseña actualizada. Ya puede iniciar sesión."})
