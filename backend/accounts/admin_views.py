from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .admin_serializers import (
    RolSerializer,
    UserAdminCreateSerializer,
    UserAdminReadSerializer,
    UserAdminUpdateSerializer,
)
from .models import Rol
from .permissions import IsAdministrador

User = get_user_model()
ADMIN_PERMS = [IsAuthenticated, IsAdministrador]


def _user_queryset():
    return User.objects.select_related("perfil__rol").order_by("username")


def _serialize_user(user):
    return UserAdminReadSerializer(user).data


@api_view(["GET"])
@permission_classes(ADMIN_PERMS)
def admin_roles_list(request):
    roles = Rol.objects.filter(activo=True).order_by("id")
    return Response(RolSerializer(roles, many=True).data)


@api_view(["GET", "POST"])
@permission_classes(ADMIN_PERMS)
def admin_usuarios_list_create(request):
    if request.method == "GET":
        qs = _user_queryset()
        q = (request.query_params.get("q") or "").strip()
        rol = (request.query_params.get("rol") or "").strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        if rol:
            qs = qs.filter(perfil__rol__codigo=rol)
        activo = request.query_params.get("activo")
        if activo in ("true", "false"):
            qs = qs.filter(is_active=(activo == "true"))
        return Response([_serialize_user(u) for u in qs])

    ser = UserAdminCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    user = _user_queryset().get(pk=user.pk)
    return Response(_serialize_user(user), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes(ADMIN_PERMS)
def admin_usuario_detail(request, user_id: int):
    try:
        user = _user_queryset().get(pk=user_id)
    except User.DoesNotExist:
        return Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(_serialize_user(user))

    if request.method == "DELETE":
        if user.pk == request.user.pk:
            return Response(
                {"detail": "No puede eliminar su propia cuenta."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    ser = UserAdminUpdateSerializer(
        data=request.data,
        partial=True,
        context={"target_user": user, "actor": request.user},
    )
    ser.is_valid(raise_exception=True)
    ser.update(user, ser.validated_data)
    user = _user_queryset().get(pk=user.pk)
    return Response(_serialize_user(user))
