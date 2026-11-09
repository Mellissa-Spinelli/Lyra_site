import json
from pathlib import Path


class Planejamento:
    """Mantém conteúdo, metodologias escolhidas e resultado do planejamento."""

    def __init__(self, arquivo_metodologias=None):
        """Prepara os dados do planejamento e carrega as metodologias."""
        if arquivo_metodologias is None:
            arquivo_metodologias = (
                Path(__file__).with_name("metodologias.json")
            )

        self.arquivo_metodologias = Path(arquivo_metodologias)

        self.metodologias = []

        self.conteudo = ""

        self.metodologias_selecionadas = []

        self.resultado = ""

        self.carregar_metodologias()

    # =====================================================
    # METODOLOGIAS
    # =====================================================

    def carregar_metodologias(self):
        """Carrega metodologias do arquivo ou inicia uma lista vazia."""
        if not self.arquivo_metodologias.exists():
            self.metodologias = []
            return

        try:
            with open(
                self.arquivo_metodologias,
                "r",
                encoding="utf-8"
            ) as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                self.metodologias = []
                return
            metodologias = dados.get("metodologias", [])
            self.metodologias = [
                item for item in metodologias
                if isinstance(item, dict)
                and isinstance(item.get("nome"), str)
                and item["nome"].strip()
            ] if isinstance(metodologias, list) else []

        except (json.JSONDecodeError, OSError, AttributeError):
            self.metodologias = []

    def salvar_metodologias(self):
        """Grava no arquivo a lista atual de metodologias."""
        dados = {
            "metodologias": self.metodologias
        }

        with open(
            self.arquivo_metodologias,
            "w",
            encoding="utf-8"
        ) as arquivo:
            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

    def adicionar_metodologia(
        self,
        nome,
        descricao=""
    ):
        """Valida e cadastra uma metodologia, retornando o novo registro."""
        nome = nome.strip()
        descricao = descricao.strip()

        if not nome:
            raise ValueError(
                "O nome da metodologia não pode ficar vazio."
            )

        for metodologia in self.metodologias:
            if metodologia["nome"].lower() == nome.lower():
                raise ValueError(
                    "Essa metodologia já está cadastrada."
                )

        nova_metodologia = {
            "nome": nome,
            "descricao": descricao
        }

        self.metodologias.append(
            nova_metodologia
        )

        self.salvar_metodologias()

        return nova_metodologia

    def remover_metodologia(self, nome):
        """Remove a metodologia pelo nome e limpa sua seleção atual."""
        nome = nome.strip().lower()

        quantidade_anterior = len(
            self.metodologias
        )

        self.metodologias = [
            metodologia
            for metodologia in self.metodologias
            if metodologia["nome"].lower() != nome
        ]

        if len(self.metodologias) == quantidade_anterior:
            return False

        self.salvar_metodologias()

        self.metodologias_selecionadas = [
            metodologia
            for metodologia in self.metodologias_selecionadas
            if metodologia["nome"].lower() != nome
        ]

        return True

    def listar_metodologias(self):
        """Retorna uma cópia da lista de metodologias cadastradas."""
        return self.metodologias.copy()

    # =====================================================
    # CONTEÚDO / HABILIDADE
    # =====================================================

    def definir_conteudo(self, conteudo):
        """Armazena o conteúdo da aula após remover espaços externos."""
        self.conteudo = conteudo.strip()

    # =====================================================
    # SELEÇÃO
    # =====================================================

    def selecionar_metodologia(self, nome):
        """Seleciona uma metodologia cadastrada sem repetir a seleção."""
        nome = nome.strip().lower()

        for metodologia in self.metodologias:

            if metodologia["nome"].lower() == nome:

                if metodologia not in self.metodologias_selecionadas:
                    self.metodologias_selecionadas.append(
                        metodologia
                    )

                return True

        return False

    def remover_selecao(self, nome):
        """Desmarca a metodologia indicada e informa se ela foi removida."""
        nome = nome.strip().lower()

        antes = len(
            self.metodologias_selecionadas
        )

        self.metodologias_selecionadas = [
            metodologia
            for metodologia in self.metodologias_selecionadas
            if metodologia["nome"].lower() != nome
        ]

        return len(
            self.metodologias_selecionadas
        ) < antes

    def limpar_selecoes(self):
        """Limpa todas as metodologias selecionadas."""
        self.metodologias_selecionadas = []

    def obter_selecionadas(self):
        """Retorna uma cópia das metodologias atualmente selecionadas."""
        return self.metodologias_selecionadas.copy()

    # =====================================================
    # DADOS PARA A IA
    # =====================================================

    def preparar_dados(self):
        """Monta o conteúdo e as metodologias no formato esperado pela IA."""
        return {
            "conteudo": self.conteudo,
            "metodologias": [
                {
                    "nome": metodologia["nome"],
                    "descricao": metodologia.get(
                        "descricao",
                        ""
                    )
                }
                for metodologia in self.metodologias_selecionadas
            ]
        }

    # =====================================================
    # RESULTADO
    # =====================================================

    def definir_resultado(self, texto):
        """Armazena o texto gerado sem espaços no início ou no fim."""
        self.resultado = texto.strip()

    def obter_resultado(self):
        """Retorna o último resultado gerado."""
        return self.resultado

    # =====================================================
    # VALIDAÇÃO
    # =====================================================

    def validar(self):
        """Confirma que há conteúdo e ao menos uma metodologia selecionada."""
        if not self.conteudo:
            raise ValueError(
                "Informe o conteúdo ou habilidade da aula."
            )

        if not self.metodologias_selecionadas:
            raise ValueError(
                "Selecione pelo menos uma metodologia."
            )

        return True
