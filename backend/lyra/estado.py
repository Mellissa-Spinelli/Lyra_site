"""
ESTADO DA CONVERSA DA LYRA

Controla situações especiais que precisam permanecer ativas
entre uma mensagem e outra.
"""


class EstadoConversa:
    """Gerencia o estado atual da conversa."""

    CONVERSANDO = "conversando"
    AGUARDANDO_AUTORIZACAO = "aguardando_autorizacao"

    ACAO_NENHUMA = None
    ACAO_CRIAR = "criar"
    ACAO_ATUALIZAR = "atualizar"

    def __init__(self):
        """Inicia a conversa sem uma autorização de memória pendente."""
        self.estado = self.CONVERSANDO

        # Memória que está temporariamente aguardando decisão.
        self.memoria_candidata = None

        # O que estamos esperando autorização para fazer.
        self.acao_memoria = self.ACAO_NENHUMA

    def aguardando_autorizacao(self):
        """Verifica se a Lyra está esperando autorização."""

        return self.estado == self.AGUARDANDO_AUTORIZACAO

    def iniciar_autorizacao(self, candidato, acao):
        """
        Coloca a conversa em estado de espera por autorização.

        acao pode ser:
        - criar
        - atualizar
        """

        if acao not in [
            self.ACAO_CRIAR,
            self.ACAO_ATUALIZAR
        ]:
            return False

        self.estado = self.AGUARDANDO_AUTORIZACAO
        self.memoria_candidata = candidato
        self.acao_memoria = acao

        return True

    def finalizar_autorizacao(self):
        """
        Retorna a conversa ao estado normal
        e limpa o candidato pendente.
        """

        self.estado = self.CONVERSANDO
        self.memoria_candidata = None
        self.acao_memoria = self.ACAO_NENHUMA

    def obter_candidato(self):
        """Retorna o candidato atual."""

        return self.memoria_candidata

    def obter_acao_memoria(self):
        """Retorna a ação que aguarda autorização."""

        return self.acao_memoria
