from conftest import auth, make_token

ANA = "11111111-1111-1111-1111-111111111111"
LUIS = "22222222-2222-2222-2222-222222222222"


# ---------- Seguridad ----------
def test_health_es_publico(client):
    assert client.get("/health").json()["status"] == "ok"


def test_endpoints_protegidos_sin_token(client):
    for method, url in [("get", "/api/me"), ("post", "/api/chat"), ("get", "/api/conversations"),
                        ("get", "/api/documents"), ("delete", "/api/documents/x")]:
        assert getattr(client, method)(url).status_code == 401, url


def test_token_invalido_y_expirado(client):
    assert client.get("/api/me", headers={"Authorization": "Bearer basura"}).status_code == 401
    expired = {"Authorization": f"Bearer {make_token(ANA, expired=True)}"}
    r = client.get("/api/me", headers=expired)
    assert r.status_code == 401 and "expiró" in r.json()["detail"]


def test_me(client):
    assert client.get("/api/me", headers=auth(ANA)).json()["id"] == ANA


# ---------- Chat ----------
def test_pregunta_respondida_con_fuentes(client):
    r = client.post("/api/chat", json={"question": "¿Quién creó a Barbie?"}, headers=auth(ANA))
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]["rejected"] is False
    assert body["answer"]["sources"]
    assert body["conversation"]["title"] == "¿Quién creó a Barbie?"


def test_pregunta_fuera_de_tema_rechazada(client):
    r = client.post("/api/chat", json={"question": "¿Cuál es la mejor receta de sushi?"}, headers=auth(ANA))
    body = r.json()
    assert body["answer"]["rejected"] is True
    assert body["answer"]["content"].startswith("No tengo suficiente información")


def test_pregunta_vacia(client):
    assert client.post("/api/chat", json={"question": ""}, headers=auth(ANA)).status_code == 422


def test_historial_por_usuario(client):
    conv = client.post("/api/chat", json={"question": "¿Quién es Ken?"}, headers=auth(ANA)).json()["conversation"]
    client.post("/api/chat", json={"question": "¿Y sus hermanas?", "conversation_id": conv["id"]}, headers=auth(ANA))

    msgs = client.get(f"/api/conversations/{conv['id']}/messages", headers=auth(ANA)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]

    # Luis no ve ni puede usar la conversación de Ana
    assert client.get("/api/conversations", headers=auth(LUIS)).json() == []
    assert client.get(f"/api/conversations/{conv['id']}/messages", headers=auth(LUIS)).status_code == 404
    r = client.post("/api/chat", json={"question": "hola", "conversation_id": conv["id"]}, headers=auth(LUIS))
    assert r.status_code == 404

    assert client.delete(f"/api/conversations/{conv['id']}", headers=auth(ANA)).status_code == 204
    assert client.get("/api/conversations", headers=auth(ANA)).json() == []


# ---------- Documentos ----------
def test_subir_listar_y_borrar_documento(client):
    files = {"file": ("peliculas.txt", b"Barbie (2023) fue dirigida por Greta Gerwig." * 50, "text/plain")}
    r = client.post("/api/documents", files=files, headers=auth(ANA))
    assert r.status_code == 202
    doc_id = r.json()["id"]

    docs = client.get("/api/documents", headers=auth(ANA)).json()
    assert docs[0]["status"] == "ready" and docs[0]["chunks"] > 0 and docs[0]["is_owner"]

    # Luis ve el documento (base compartida) pero no puede borrarlo
    assert client.get("/api/documents", headers=auth(LUIS)).json()[0]["is_owner"] is False
    assert client.delete(f"/api/documents/{doc_id}", headers=auth(LUIS)).status_code == 403

    assert client.delete(f"/api/documents/{doc_id}", headers=auth(ANA)).status_code == 204
    assert client.get("/api/documents", headers=auth(ANA)).json() == []


def test_formato_no_permitido(client):
    files = {"file": ("virus.exe", b"MZ...", "application/octet-stream")}
    r = client.post("/api/documents", files=files, headers=auth(ANA))
    assert r.status_code == 400 and "Formato no permitido" in r.json()["detail"]


def test_archivo_vacio(client):
    files = {"file": ("vacio.txt", b"", "text/plain")}
    assert client.post("/api/documents", files=files, headers=auth(ANA)).status_code == 400


# ---------- Integración con el agente ----------
def test_agente_con_error_devuelve_503_y_no_guarda_nada(client, monkeypatch):
    from services.mock_agent import MockAgent

    def caido(self, question, user_id, history):
        return {"answer": "El modelo no está disponible.", "rejected": True, "sources": [], "error": True}

    monkeypatch.setattr(MockAgent, "ask", caido)
    r = client.post("/api/chat", json={"question": "¿Quién es Ken?"}, headers=auth(ANA))
    assert r.status_code == 503 and r.json()["detail"] == "El modelo no está disponible."
    assert client.get("/api/conversations", headers=auth(ANA)).json() == []


def test_fuentes_con_formato_del_agente(client):
    body = client.post("/api/chat", json={"question": "¿Quién es Ken?"}, headers=auth(ANA)).json()
    fuente = body["answer"]["sources"][0]
    assert fuente["document"] == "personajes.md" and fuente["fragment"]


def test_documento_de_la_base_inicial_no_se_borra(client):
    from repositories import get_repository

    repo = get_repository()
    doc = repo.create_document(ANA, "03-ken.md", None, 0)
    repo.update_document(doc["id"], user_id=None, status="ready")
    lista = client.get("/api/documents", headers=auth(ANA)).json()
    assert lista[0]["is_owner"] is False
    assert client.delete(f"/api/documents/{doc['id']}", headers=auth(ANA)).status_code == 403
