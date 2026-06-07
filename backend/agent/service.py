"""Orquestación del chat: caché, herramientas y fallback entre modelos Gemini."""

from __future__ import annotations



from typing import Any



from django.conf import settings



from .cache import get_cached_agent_response, set_cached_agent_response

from .gemini import (

    GeminiError,

    GeminiRateLimitError,

    alternate_model_id,

    extract_function_calls,

    extract_text,

    generate_content,

    model_id,

    model_response_part,

)

from .tools import execute_tool, get_tool_declarations



SYSTEM_PROMPT_PUBLIC = """Eres un asistente del sistema SG Mitigación de Accidentes (Medellín, Colombia).

Respondes SIEMPRE en español claro y conciso.



Puedes consultar datos históricos de incidentes mediante herramientas (KPIs, rankings, evolución,

distribuciones y patrones temporales). Los datos provienen de la base del proyecto.



Reglas:

- Si no conoces el rango de fechas, llama primero a get_rango_fechas o get_catalogos.

- Usa filtros (comuna_id, barrio_id, clase_incidente_id) solo cuando el usuario los mencione.

- NO inventes cifras: usa exclusivamente los resultados de las herramientas.

- NO puedes acceder a predicciones ni modelos proyectivos; si te lo piden, indica que debe

  iniciar sesión como analista para habilitar esas consultas en este asistente.

- Cita periodos y filtros aplicados en tu respuesta.

- Si los datos no están disponibles, dilo con transparencia.

"""



SYSTEM_PROMPT_ANALYST = """Eres un asistente del sistema SG Mitigación de Accidentes (Medellín, Colombia).

Respondes SIEMPRE en español claro y conciso.



El usuario tiene sesión iniciada como ANALISTA. Puedes usar:

1) Datos históricos (KPIs, rankings, evolución, distribuciones, patrones temporales).

2) Predicciones y proyecciones (series mensuales, prioridad territorial, carga esperada,

   patrones temporales proyectados).



Reglas:

- Para preguntas sobre meses futuros o sectores con mayor carga proyectada, usa las herramientas

  de predicción (p. ej. get_predicciones_mensuales con horizonte_meses=6 y get_prioridad_territorial

  o get_carga_esperada_territorial para identificar sectores).

- Si no conoces el rango de fechas histórico, llama a get_rango_fechas o get_catalogos.

- NO inventes cifras: usa exclusivamente los resultados de las herramientas.

- Indica que las proyecciones son estimaciones modeladas, no hechos observados.

- Cita periodos, horizonte en meses y filtros aplicados.

"""





def _system_prompt(is_analista: bool) -> str:

    return SYSTEM_PROMPT_ANALYST if is_analista else SYSTEM_PROMPT_PUBLIC





def _build_contents(message: str, history: list[dict[str, str]] | None) -> list[dict[str, Any]]:

    contents: list[dict[str, Any]] = []

    for turn in (history or [])[-6:]:

        role = turn.get("role")

        text = (turn.get("content") or "").strip()

        if not text or role not in ("user", "assistant"):

            continue

        gemini_role = "user" if role == "user" else "model"

        contents.append({"role": gemini_role, "parts": [{"text": text}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    return contents





def _run_gemini_loop(

    *,

    model: str,

    contents: list[dict[str, Any]],

    is_analista: bool = False,

    max_rounds: int = 5,

) -> tuple[str, list[str], str]:

    """Devuelve (respuesta_texto, herramientas_usadas, model_id)."""

    tools_used: list[str] = []

    conversation = list(contents)

    tools = get_tool_declarations(is_analista)

    system_instruction = _system_prompt(is_analista)



    for _ in range(max_rounds):

        response = generate_content(

            model=model,

            contents=conversation,

            tools=tools,

            system_instruction=system_instruction,

        )

        calls = extract_function_calls(response)

        if not calls:

            text = extract_text(response)

            if text:

                return text.strip(), tools_used, model

            raise GeminiError("Gemini no devolvió texto ni llamadas a herramientas.")



        model_part = model_response_part(response)

        if model_part:

            conversation.append(model_part)



        response_parts: list[dict[str, Any]] = []

        for call in calls:

            name = call.get("name") or ""

            args = call.get("args") or {}

            tools_used.append(name)

            result = execute_tool(name, args, is_analista=is_analista)

            response_parts.append(

                {

                    "functionResponse": {

                        "name": name,

                        "response": result,

                    }

                }

            )

        conversation.append({"role": "user", "parts": response_parts})



    raise GeminiError("Se alcanzó el máximo de rondas de herramientas sin respuesta final.")





def run_agent_chat(

    *,

    message: str,

    model_preference: str = "flash",

    history: list[dict[str, str]] | None = None,

    skip_cache: bool = False,

    is_analista: bool = False,

) -> dict[str, Any]:

    message = (message or "").strip()

    if not message:

        raise ValueError("El mensaje no puede estar vacío.")

    if len(message) > 2000:

        raise ValueError("El mensaje es demasiado largo (máx. 2000 caracteres).")



    if not skip_cache:

        cached = get_cached_agent_response(message, is_analista=is_analista)

        if cached:

            return {

                **cached,

                "from_cache": True,

                "model_requested": model_preference,

                "is_analista": is_analista,

            }



    primary = model_id(model_preference)

    fallback = alternate_model_id(model_preference)

    contents = _build_contents(message, history)



    model_used = primary

    fallback_used = False

    try:

        answer, tools_used, model_used = _run_gemini_loop(

            model=primary, contents=contents, is_analista=is_analista

        )

    except GeminiRateLimitError:

        fallback_used = True

        model_used = fallback

        try:

            answer, tools_used, model_used = _run_gemini_loop(

                model=fallback, contents=contents, is_analista=is_analista

            )

        except GeminiRateLimitError as exc:

            raise GeminiError(

                "Se agotó la cuota de ambos modelos (Flash y Flash-Lite). "

                "Intente más tarde o reformule una pregunta ya respondida (caché)."

            ) from exc



    payload = {

        "answer": answer,

        "model_used": model_used,

        "model_requested": model_preference,

        "fallback_used": fallback_used,

        "tools_used": tools_used,

        "from_cache": False,

        "is_analista": is_analista,

    }

    set_cached_agent_response(message, payload, is_analista=is_analista)

    return payload





def agent_info_payload(*, is_analista: bool = False) -> dict[str, Any]:

    scope_public = (

        "Consulta datos históricos del tablero y mapa sin iniciar sesión. "

        "Las predicciones requieren iniciar sesión como analista."

    )

    scope_analyst = (

        "Sesión de analista activa: puede consultar datos históricos y predicciones "

        "(proyecciones mensuales, prioridad territorial, carga esperada y patrones proyectados)."

    )

    return {

        "is_analista": is_analista,

        "predictions_enabled": is_analista,

        "models": [

            {

                "id": "flash",

                "label": "Gemini 2.5 Flash",

                "description": "Mejor equilibrio entre calidad y consumo de cuota.",

                "model_id": model_id("flash"),

            },

            {

                "id": "flash-lite",

                "label": "Gemini 2.5 Flash-Lite",

                "description": "Más consultas disponibles; respuestas algo más simples.",

                "model_id": model_id("flash-lite"),

            },

        ],

        "disclaimer": {

            "quota": (

                "Este asistente usa la API gratuita de Google Gemini, con límites diarios y por minuto "

                "que varían según el modelo. Si se agota la cuota de un modelo, el sistema intentará "

                "automáticamente el otro."

            ),

            "privacy": (

                "Según las políticas de Google para el tier gratuito, las consultas enviadas pueden "

                "utilizarse para mejorar sus productos y servicios. No envíe información personal "

                "o confidencial."

            ),

            "scope": scope_analyst if is_analista else scope_public,

        },

        "cache_enabled": int(getattr(settings, "AGENT_CACHE_TTL", 0)) > 0,

        "daily_limit_per_ip": int(getattr(settings, "AGENT_DAILY_LIMIT_PER_IP", 0)),

    }


