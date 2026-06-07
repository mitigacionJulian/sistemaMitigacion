import pytest

from unittest.mock import patch



from django.contrib.auth import get_user_model

from django.urls import reverse



from accounts.models import PerfilUsuario, Rol



User = get_user_model()





@pytest.mark.django_db

def test_agent_info_public():

    c = __import__("rest_framework.test", fromlist=["APIClient"]).APIClient()

    r = c.get(reverse("agent-info"))

    assert r.status_code == 200

    assert r.data["predictions_enabled"] is False

    assert "models" in r.data

    assert "disclaimer" in r.data





@pytest.mark.django_db

def test_agent_info_analista():

    from rest_framework.test import APIClient



    analista = Rol.objects.get(codigo="analista")

    user = User.objects.create_user(username="ag1", password="ClaveSegura123!")

    PerfilUsuario.objects.create(user=user, rol=analista, telefono="573003333333")



    c = APIClient()

    login = c.post(

        reverse("auth-login"),

        {"username": "ag1", "password": "ClaveSegura123!"},

        format="json",

    )

    c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    r = c.get(reverse("agent-info"))

    assert r.status_code == 200

    assert r.data["predictions_enabled"] is True

    assert r.data["is_analista"] is True





@pytest.mark.django_db

def test_agent_chat_requires_message():

    from rest_framework.test import APIClient



    c = APIClient()

    r = c.post(reverse("agent-chat"), {"message": ""}, format="json")

    assert r.status_code == 400





@pytest.mark.django_db

def test_agent_chat_public_no_jwt():

    fake = {

        "answer": "Hay 1.234 incidentes en el periodo.",

        "model_used": "gemini-2.5-flash",

        "model_requested": "flash",

        "fallback_used": False,

        "tools_used": ["get_kpis"],

        "from_cache": False,

        "is_analista": False,

    }

    with patch("agent.views.run_agent_chat", return_value=fake) as mock_run:

        from rest_framework.test import APIClient



        c = APIClient()

        r = c.post(

            reverse("agent-chat"),

            {"message": "¿Cuántos incidentes hay?", "model": "flash"},

            format="json",

        )

    assert r.status_code == 200

    assert mock_run.call_args.kwargs["is_analista"] is False





@pytest.mark.django_db

def test_agent_chat_analista_enables_predictions():

    from rest_framework.test import APIClient



    analista = Rol.objects.get(codigo="analista")

    user = User.objects.create_user(username="ag2", password="ClaveSegura123!")

    PerfilUsuario.objects.create(user=user, rol=analista, telefono="573004444444")



    fake = {

        "answer": "En el mes 3 se proyecta mayor carga en Comuna 10.",

        "model_used": "gemini-2.5-flash",

        "model_requested": "flash",

        "fallback_used": False,

        "tools_used": ["get_predicciones_mensuales", "get_prioridad_territorial"],

        "from_cache": False,

        "is_analista": True,

    }

    with patch("agent.views.run_agent_chat", return_value=fake) as mock_run:

        c = APIClient()

        login = c.post(

            reverse("auth-login"),

            {"username": "ag2", "password": "ClaveSegura123!"},

            format="json",

        )

        c.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        r = c.post(

            reverse("agent-chat"),

            {"message": "¿Qué mes aumenta en 6 meses?", "model": "flash"},

            format="json",

        )

    assert r.status_code == 200

    assert mock_run.call_args.kwargs["is_analista"] is True

    assert r.data["predictions_enabled"] is True





@pytest.mark.django_db

def test_analyst_tools_blocked_for_public():

    from agent.tools import execute_tool



    r = execute_tool("get_predicciones_mensuales", {"horizonte_meses": 6}, is_analista=False)

    assert r["ok"] is False

    assert "analista" in r["error"].lower()





@pytest.mark.django_db

def test_analyst_tools_available_for_analista():

    from agent.tools import get_tool_declarations



    public = {t["name"] for t in get_tool_declarations(False)}

    analyst = {t["name"] for t in get_tool_declarations(True)}

    assert "get_predicciones_mensuales" not in public

    assert "get_predicciones_mensuales" in analyst

    assert "get_prioridad_territorial" in analyst





@pytest.mark.django_db

def test_normalize_question_cache_key_scopes():

    from agent.cache import agent_response_cache_key



    k_public = agent_response_cache_key("misma pregunta", is_analista=False)

    k_analyst = agent_response_cache_key("misma pregunta", is_analista=True)

    assert k_public != k_analyst


