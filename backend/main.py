"""API autenticada do núcleo LYRA para o site hospedado."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from planejamento import Planejamento  # noqa: E402


metodologias = Planejamento(BACKEND_DIR / "metodologias.json").listar_metodologias()
lyra_controller = None
ai_lock = Lock()
auth_lock = Lock()
login_failures: deque[float] = deque()
ai_requests: deque[float] = deque()
TOKEN_LIFETIME_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_FAILURE_LIMIT = 10
AI_WINDOW_SECONDS = 60
AI_REQUEST_LIMIT = 20
MAX_REQUEST_BYTES = 64_000


def get_controller():
    global lyra_controller
    if lyra_controller is None:
        from lyra.controller import LyraController

        lyra_controller = LyraController()
    return lyra_controller


def json_safe(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue_token() -> str:
    expires_at = int(time.time()) + TOKEN_LIFETIME_SECONDS
    payload = json.dumps(
        {"exp": expires_at, "nonce": secrets.token_urlsafe(12)},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = _b64(payload)
    signature = hmac.new(
        os.environ["LYRA_SESSION_SECRET"].encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded}.{_b64(signature)}"


def valid_token(token: str) -> bool:
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.new(
            os.environ["LYRA_SESSION_SECRET"].encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest())
        if not hmac.compare_digest(signature, expected):
            return False
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        return type(payload.get("exp")) is int and payload["exp"] > int(time.time())
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


class LyraApiHandler(BaseHTTPRequestHandler):
    server_version = "LyraAPI/1.0"

    def send_json(self, payload, status=200):
        body = json_safe(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        origin = self.headers.get("Origin", "")
        allowed = {
            value.strip().rstrip("/")
            for value in os.getenv(
                "LYRA_ALLOWED_ORIGINS",
                "https://mellissa-spinelli.github.io",
            ).split(",")
            if value.strip()
        }
        if origin.rstrip("/") in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Max-Age", "600")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Tamanho da solicitação inválido.") from None
        if length < 1 or length > MAX_REQUEST_BYTES:
            raise ValueError("Envie um formulário válido.")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("O conteúdo enviado não está em formato válido.") from None
        if not isinstance(payload, dict):
            raise ValueError("Envie os dados em formato de objeto.")
        return payload

    def _is_authenticated(self):
        authorization = self.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        return scheme.lower() == "bearer" and bool(token) and valid_token(token)

    def _require_auth(self):
        if not self._is_authenticated():
            self.send_json({"error": "Conecte-se à sua conta LYRA para continuar."}, 401)
            return False
        return True

    def _allow_ai_request(self):
        now = time.monotonic()
        with auth_lock:
            while ai_requests and now - ai_requests[0] >= AI_WINDOW_SECONDS:
                ai_requests.popleft()
            if len(ai_requests) >= AI_REQUEST_LIMIT:
                return False
            ai_requests.append(now)
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json({"ok": True})
            return
        if path == "/api/metodologias":
            self.send_json({"metodologias": metodologias})
            return
        if path == "/api/auth/me":
            if self._require_auth():
                self.send_json({"ok": True})
            return
        self.send_json({"error": "Rota não encontrada."}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/auth/login":
                self._handle_login(payload)
            elif path in {"/api/chat", "/api/planejamento"}:
                if not self._require_auth():
                    return
                if not self._allow_ai_request():
                    self.send_json({"error": "Muitas solicitações em sequência. Aguarde um minuto."}, 429)
                    return
                if path == "/api/chat":
                    self._handle_chat(payload)
                else:
                    self._handle_planning(payload)
            else:
                self.send_json({"error": "Rota não encontrada."}, 404)
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except RuntimeError:
            self.send_json({"error": "O núcleo de IA não está configurado no servidor."}, 503)
        except Exception:
            self.send_json({"error": "Não foi possível concluir a solicitação agora."}, 502)

    def _handle_login(self, payload):
        password = payload.get("password")
        configured_password = os.getenv("LYRA_ACCESS_PASSWORD", "")
        session_secret = os.getenv("LYRA_SESSION_SECRET", "")
        if len(configured_password) < 12 or len(session_secret) < 32:
            self.send_json({"error": "O acesso ao backend ainda não foi configurado."}, 503)
            return
        if not isinstance(password, str) or not password:
            raise ValueError("Digite a senha de acesso da LYRA.")

        now = time.monotonic()
        with auth_lock:
            while login_failures and now - login_failures[0] >= LOGIN_WINDOW_SECONDS:
                login_failures.popleft()
            if len(login_failures) >= LOGIN_FAILURE_LIMIT:
                self.send_json({"error": "Muitas tentativas. Aguarde alguns minutos e tente novamente."}, 429)
                return
            password_ok = hmac.compare_digest(password, configured_password)
            if not password_ok:
                login_failures.append(now)
            else:
                login_failures.clear()

        if not password_ok:
            self.send_json({"error": "Senha incorreta."}, 401)
            return
        self.send_json({"token": issue_token(), "expires_in": TOKEN_LIFETIME_SECONDS})

    def _handle_chat(self, payload):
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Escreva uma mensagem antes de enviar.")
        if len(message) > 8_000:
            raise ValueError("A mensagem é longa demais.")
        with ai_lock:
            response = get_controller().enviar(message.strip())
        self.send_json({"response": response})

    def _handle_planning(self, payload):
        content = payload.get("content")
        selected_names = payload.get("methods")
        audience = payload.get("audience", "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Informe o tema ou conteúdo da aula.")
        if not isinstance(selected_names, list) or not selected_names:
            raise ValueError("Selecione ao menos uma abordagem.")
        if any(not isinstance(name, str) for name in selected_names):
            raise ValueError("Confira as metodologias selecionadas.")
        if len(content) > 8_000:
            raise ValueError("O conteúdo é longo demais.")
        selected = [method for method in metodologias if method.get("nome") in selected_names]
        if not selected:
            raise ValueError("Selecione uma metodologia disponível.")
        prompt_content = content.strip()
        if isinstance(audience, str) and audience.strip():
            prompt_content += f"\n\nTurma ou faixa etária: {audience.strip()[:200]}"
        with ai_lock:
            response = get_controller().gerar_metodologia(prompt_content, selected)
        if not response or not response.strip():
            self.send_json({"error": "A LYRA não recebeu uma resposta. Tente novamente."}, 502)
            return
        self.send_json({"response": response.strip()})

    def log_message(self, format, *args):
        # Não registra o conteúdo das conversas nem cabeçalhos de autenticação.
        print(f"[LYRA API] {self.client_address[0]} - {format % args}")


def main():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), LyraApiHandler)
    print(f"API LYRA disponível na porta {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
