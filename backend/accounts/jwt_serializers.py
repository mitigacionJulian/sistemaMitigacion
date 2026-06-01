from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import UserMeSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        perfil = getattr(user, "perfil", None)
        if perfil is not None:
            token["rol"] = perfil.rol.codigo
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserMeSerializer(self.user).data
        return data
