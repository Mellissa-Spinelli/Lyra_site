"""
SISTEMA DE MEMÓRIA DA LYRA

Responsável por:
- armazenar memórias;
- consultar memórias;
- atualizar memórias;
- esquecer memórias.

Este módulo é responsável pela lógica.
O arquivo JSON é apenas o armazenamento.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path


class MemoriaLyra:
    """Gerenciador da memória permanente da Lyra."""

    def __init__(self, caminho="dados/memoria_lyra.json"):
        """Carrega memórias usando um caminho estável dentro do projeto."""
        if caminho == "dados/memoria_lyra.json":
            caminho = Path(__file__).resolve().parents[1] / caminho
        self.caminho = str(caminho)
        self.memoria = self._carregar()

    # ============================================================
    # CARREGAMENTO
    # ============================================================

    def _carregar(self):
        """Carrega as memórias existentes no arquivo JSON."""

        if not os.path.exists(self.caminho):
            return []

        try:
            with open(self.caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                return []
            memorias = dados.get("memorias", [])
            return [item for item in memorias if isinstance(item, dict)] if isinstance(memorias, list) else []

        except (json.JSONDecodeError, OSError):
            return []

    # ============================================================
    # SALVAMENTO
    # ============================================================

    def _salvar(self):
        """Salva as memórias no arquivo JSON."""

        pasta = os.path.dirname(self.caminho)

        if pasta:
            os.makedirs(pasta, exist_ok=True)

        with open(self.caminho, "w", encoding="utf-8") as arquivo:
            json.dump(
                {"memorias": self.memoria},
                arquivo,
                ensure_ascii=False,
                indent=4
            )

    # ============================================================
    # ADICIONAR
    # ============================================================

    def adicionar(
        self,
        categoria,
        conteudo,
        origem="usuaria",
        autorizada=True
    ):
        """
        Adiciona uma nova memória.

        categoria:
            fatos, preferencias, projetos, objetivos,
            rotina, relacoes, memorias_sociais ou padroes.

        conteudo:
            Informação que será armazenada.

        origem:
            De onde veio a informação.

        autorizada:
            Indica se Mell autorizou o armazenamento.
        """

        if not conteudo or not conteudo.strip():
            return None

        if not autorizada:
            return None

        agora = datetime.now().isoformat(timespec="seconds")

        memoria = {
            "id": str(uuid.uuid4()),
            "categoria": categoria,
            "conteudo": conteudo.strip(),
            "origem": origem,
            "criada_em": agora,
            "atualizada_em": agora,
            "status": "ativa"
        }

        self.memoria.append(memoria)

        self._salvar()

        return memoria

    # ============================================================
    # CONSULTAR
    # ============================================================

    def listar(self, categoria=None):
        """
        Retorna as memórias ativas.

        Se uma categoria for informada, retorna somente
        memórias daquela categoria.
        """

        memorias = [
            memoria
            for memoria in self.memoria
            if memoria.get("status") == "ativa"
        ]

        if categoria:
            memorias = [
                memoria
                for memoria in memorias
                if memoria.get("categoria") == categoria
            ]

        return memorias

    # ============================================================
    # BUSCAR
    # ============================================================

    def buscar(self, termo):
        """Busca memórias pelo conteúdo."""

        if not termo:
            return []

        termo = termo.lower()

        resultados = []

        for memoria in self.listar():
            conteudo = memoria.get("conteudo", "").lower()

            if termo in conteudo:
                resultados.append(memoria)

        return resultados

    # ============================================================
    # ATUALIZAR
    # ============================================================

    def atualizar(self, memoria_id, novo_conteudo):
        """Atualiza o conteúdo de uma memória existente."""

        if not novo_conteudo or not novo_conteudo.strip():
            return False

        for memoria in self.memoria:

            if memoria.get("id") == memoria_id:

                memoria["conteudo"] = novo_conteudo.strip()

                memoria["atualizada_em"] = datetime.now().isoformat(
                    timespec="seconds"
                )

                self._salvar()

                return True

        return False

    # ============================================================
    # ESQUECER
    # ============================================================

    def esquecer(self, memoria_id):
        """
        Remove uma memória logicamente.

        A memória não é destruída imediatamente do arquivo.
        Ela passa para o estado 'arquivada'.
        """

        for memoria in self.memoria:

            if memoria.get("id") == memoria_id:

                memoria["status"] = "arquivada"

                memoria["atualizada_em"] = datetime.now().isoformat(
                    timespec="seconds"
                )

                self._salvar()

                return True

        return False

    # ============================================================
    # CONTAGEM
    # ============================================================

    def quantidade(self):
        """Retorna a quantidade de memórias ativas."""

        return len(self.listar())

    def aplicar_atualizacao(self, memoria_id, novo_conteudo):
        """
        Atualiza uma memória existente com um novo conteúdo.

        Retorna True se a atualização for realizada.
        """

        if not memoria_id:
            return False

        if not novo_conteudo or not novo_conteudo.strip():
            return False

        return self.atualizar(
            memoria_id,
            novo_conteudo.strip()
        )

    def buscar_por_conteudo(self, texto):
        """
        Procura memórias ativas cujo conteúdo contenha
        o texto informado.

        Retorna uma lista de memórias encontradas.
        """

        if not texto:
            return []

        texto = texto.lower().strip()

        resultados = []

        for memoria in self.listar():

            conteudo = memoria.get(
                "conteudo",
                ""
            ).lower()

            if texto in conteudo:
                resultados.append(memoria)

        return resultados
