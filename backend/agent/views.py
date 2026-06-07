from rest_framework import status

from rest_framework.decorators import api_view, permission_classes

from rest_framework.permissions import AllowAny

from rest_framework.response import Response



from .auth import user_is_analista

from .cache import check_daily_ip_limit, increment_daily_ip_limit

from .gemini import GeminiError

from .service import agent_info_payload, run_agent_chat





@api_view(["GET"])

@permission_classes([AllowAny])

def agent_info_view(request):

    """Metadatos públicos; si hay JWT de analista, indica predicciones habilitadas."""

    is_analista = user_is_analista(request)

    return Response(agent_info_payload(is_analista=is_analista))





@api_view(["POST"])

@permission_classes([AllowAny])

def agent_chat_view(request):

    """

    Chat del asistente. Público (AllowAny): no requiere JWT.

    Si el cliente envía JWT de analista, habilita herramientas de predicción.

    """

    is_analista = user_is_analista(request)



    allowed, used, limit = check_daily_ip_limit(request)

    if not allowed:

        return Response(

            {

                "detail": (

                    f"Límite diario de consultas alcanzado ({limit} por día). "

                    "Intente mañana o reformule preguntas ya respondidas (caché)."

                ),

                "code": "daily_limit",

                "used": used,

                "limit": limit,

            },

            status=status.HTTP_429_TOO_MANY_REQUESTS,

        )



    body = request.data if isinstance(request.data, dict) else {}

    message = (body.get("message") or "").strip()

    model_preference = (body.get("model") or "flash").strip().lower()

    history = body.get("history") if isinstance(body.get("history"), list) else []

    skip_cache = bool(body.get("skip_cache"))



    if model_preference not in ("flash", "flash-lite", "lite", "flash_lite"):

        model_preference = "flash"



    try:

        result = run_agent_chat(

            message=message,

            model_preference=model_preference,

            history=history,

            skip_cache=skip_cache,

            is_analista=is_analista,

        )

    except ValueError as exc:

        return Response({"detail": str(exc), "code": "invalid_input"}, status=status.HTTP_400_BAD_REQUEST)

    except GeminiError as exc:

        return Response(

            {"detail": str(exc), "code": "gemini_error"},

            status=status.HTTP_503_SERVICE_UNAVAILABLE,

        )



    if not result.get("from_cache"):

        increment_daily_ip_limit(request)



    quota = check_daily_ip_limit(request)

    result["quota"] = {

        "used": quota[1],

        "limit": quota[2],

        "remaining": max(0, quota[2] - quota[1]) if quota[2] > 0 else None,

    }

    result["predictions_enabled"] = is_analista

    return Response(result)


