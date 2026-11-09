"""Servidor local do site LYRA, com acesso ao núcleo Python existente."""

from __future__ import annotations

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import unquote, urlparse


WEB_DIR = Path(__file__).resolve().parent
PROJECT_DIR = WEB_DIR.parent / "projetoLYRA"
sys.path.insert(0, str(PROJECT_DIR))

from agenda import AgendaSemanal, DIAS, HORARIOS_TURNO, ORDEM_TURNO  # noqa: E402
from planejamento import Planejamento  # noqa: E402


AGENDA_FILE = PROJECT_DIR / "agenda_lyra.json"
agenda = AgendaSemanal(AGENDA_FILE)
agenda_lock = Lock()
ai_lock = Lock()
lyra_controller = None
metodologias = Planejamento().listar_metodologias()


def get_controller():
    global lyra_controller
    if lyra_controller is None:
        from lyra.controller import LyraController

        lyra_controller = LyraController()
    return lyra_controller


def json_safe(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class LyraHandler(SimpleHTTPRequestHandler):
    """Serve a interface e os endpoints usados pelo site local."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def send_json(self, payload, status=200):
        body = json_safe(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Tamanho da requisição inválido.") from None
        if length < 1 or length > 64_000:
            raise ValueError("Envie um formulário válido.")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("O conteúdo enviado não está em formato válido.") from None
        if not isinstance(payload, dict):
            raise ValueError("Envie os dados em formato de objeto.")
        return payload

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json({"ok": True})
            return
        if path == "/api/metodologias":
            self.send_json({"metodologias": metodologias})
            return
        if path == "/api/agenda":
            with agenda_lock:
                aulas = []
                for aula in agenda.aulas:
                    item = dict(aula)
                    turno = item.get("turno")
                    ordem = item.get("ordem", 0)
                    if not item.get("horario") and turno == "matutina":
                        item["horario_exibicao"] = agenda.horario_matutino(ordem)
                    elif (not item.get("horario") and turno in HORARIOS_TURNO
                          and type(ordem) is int and 1 <= ordem <= len(HORARIOS_TURNO[turno])):
                        item["horario_exibicao"] = HORARIOS_TURNO[turno][ordem - 1]
                    else:
                        item["horario_exibicao"] = item.get("horario", "")
                    aulas.append(item)
            aulas.sort(key=lambda aula: (
                aula.get("dia", 0),
                ORDEM_TURNO.get(aula.get("turno"), 0),
                aula.get("ordem", 0),
                aula.get("horario", ""),
            ))
            self.send_json({"dias": DIAS, "aulas": aulas})
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/chat":
                self.handle_chat(payload)
            elif path == "/api/planejamento":
                self.handle_planning(payload)
            elif path == "/api/agenda":
                self.handle_add_lesson(payload)
            else:
                self.send_json({"error": "Rota não encontrada."}, 404)
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except RuntimeError:
            self.send_json({
                "error": "O núcleo de IA não está configurado. Confira a OPENAI_API_KEY no arquivo .env do projeto LYRA."
            }, 503)
        except Exception:
            self.send_json({"error": "Não foi possível concluir a solicitação agora."}, 502)

    def do_DELETE(self):
        path = urlparse(self.path).path
        prefix = "/api/agenda/"
        if not path.startswith(prefix):
            self.send_json({"error": "Rota não encontrada."}, 404)
            return
        aula_id = unquote(path[len(prefix):]).strip()
        if not aula_id:
            self.send_json({"error": "Aula não identificada."}, 400)
            return
        with agenda_lock:
            aulas_atualizadas = [aula for aula in agenda.aulas if aula.get("id") != aula_id]
            if len(aulas_atualizadas) == len(agenda.aulas):
                self.send_json({"error": "Aula não encontrada."}, 404)
                return
            agenda.aulas = aulas_atualizadas
            agenda.salvar()
        self.send_json({"ok": True})

    def handle_chat(self, payload):
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Escreva uma mensagem antes de enviar.")
        if len(message) > 8_000:
            raise ValueError("A mensagem é longa demais.")
        with ai_lock:
            response = get_controller().enviar(message.strip())
        self.send_json({"response": response})

    def handle_planning(self, payload):
        content = payload.get("content")
        selected_names = payload.get("methods")
        audience = payload.get("audience", "")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Informe o tema ou conteúdo da aula.")
        if not isinstance(selected_names, list) or not selected_names:
            raise ValueError("Selecione ao menos uma abordagem.")
        if len(content) > 8_000:
            raise ValueError("O conteúdo é longo demais.")
        selected = [
            method for method in metodologias
            if method.get("nome") in selected_names
        ]
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

    def handle_add_lesson(self, payload):
        day = payload.get("day")
        time = payload.get("time")
        discipline = payload.get("discipline")
        summary = payload.get("summary", "")
        materials = payload.get("materials", "")
        if type(day) is not int or not 0 <= day < len(DIAS):
            raise ValueError("Escolha um dia da semana válido.")
        if not isinstance(time, str) or not time.strip():
            raise ValueError("Informe o horário da aula.")
        if len(time) > 40:
            raise ValueError("O horário informado é longo demais.")
        if not isinstance(discipline, str) or not discipline.strip():
            raise ValueError("Informe a disciplina.")
        if not isinstance(summary, str) or not isinstance(materials, str):
            raise ValueError("Confira os detalhes da aula.")
        if len(discipline) > 120 or len(summary) > 2_000 or len(materials) > 2_000:
            raise ValueError("Um dos campos ultrapassou o tamanho permitido.")
        with agenda_lock:
            agenda.salvar_planejamento(
                DIAS[day], time.strip(), discipline.strip(), summary, materials
            )
            aulas = [dict(aula) for aula in agenda.aulas]
        self.send_json({"ok": True, "aulas": aulas}, 201)

    def log_message(self, format, *args):
        print(f"[LYRA web] {self.address_string()} - {format % args}")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), LyraHandler)
    print("LYRA Web disponível em http://127.0.0.1:8000")
    print("Servidor local: as mensagens e a chave de IA permanecem no seu computador.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando o servidor da LYRA.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
