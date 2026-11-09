import os

from dotenv import load_dotenv
from openai import OpenAI

from lyra.personalidade import obter_personalidade
from lyra.contexto import obter_contexto
from lyra.memoria import MemoriaLyra
from lyra.memoria_inteligente import MemoriaInteligente
from lyra.estado import EstadoConversa


class LyraIA:
    """Núcleo responsável pela comunicação da LYRA com a IA."""

    def __init__(self, modelo="gpt-5-mini"):
        """Configura o cliente de IA, a memória e o histórico da conversa."""
        load_dotenv()

        chave = os.getenv("OPENAI_API_KEY")

        if not chave:
            raise RuntimeError(
                "OPENAI_API_KEY não encontrada. "
                "Verifique o arquivo .env."
            )

        self.cliente = OpenAI(
            api_key=chave,
            timeout=30.0,
            max_retries=0,
        )
        self.modelo = modelo

        # ========================================================
        # IDENTIDADE
        # ========================================================

        self.personalidade = obter_personalidade()

        # ========================================================
        # CONTEXTO DO SISTEMA
        # ========================================================

        self.contexto = obter_contexto()

        # ========================================================
        # MEMÓRIA PERMANENTE
        # ========================================================

        caminho_memoria = os.getenv("LYRA_MEMORY_PATH", "dados/memoria_lyra.json")
        self.memoria = MemoriaLyra(caminho_memoria)

        # ========================================================
        # SISTEMA DE MEMÓRIA INTELIGENTE
        # ========================================================

        self.memoria_inteligente = MemoriaInteligente(
            self.cliente,
            self.modelo
        )

        # ========================================================
        # ESTADO DA CONVERSA
        # ========================================================

        self.estado = EstadoConversa()

        # ========================================================
        # HISTÓRICO DA CONVERSA ATUAL
        # ========================================================

        self.historico = []

    # ============================================================
    # MEMÓRIA
    # ============================================================

    def _obter_memorias_ativas(self):
        """Retorna as memórias permanentes atualmente ativas."""

        return self.memoria.listar()

    def _formatar_memorias(self):
        """Transforma as memórias em contexto para a IA."""

        memorias = self._obter_memorias_ativas()

        if not memorias:
            return "Nenhuma memória permanente disponível."

        linhas = []

        for memoria in memorias:
            categoria = memoria.get(
                "categoria",
                "sem categoria"
            )

            conteudo = memoria.get(
                "conteudo",
                ""
            )

            linhas.append(
                f"- [{categoria}] {conteudo}"
            )

        return "\n".join(linhas)

    # ============================================================
    # INSTRUÇÕES DA LYRA
    # ============================================================

    def _criar_instrucoes(self):
        """Monta as instruções completas da Lyra."""

        memorias = self._formatar_memorias()

        return f"""
{self.personalidade}

========================
CONTEXTO ATUAL DO SISTEMA
========================

{self.contexto}

========================
MEMÓRIA PERMANENTE
========================

As informações abaixo são memórias permanentes atualmente
ativas sobre Mell.

Use essas informações quando forem relevantes.

Não trate inferências como fatos.

Não invente informações que não estejam presentes na memória.

MEMÓRIAS:

{memorias}
"""

    # ============================================================
    # DETECÇÃO DE INTENÇÕES DO SISTEMA
    # ============================================================

    def _eh_consulta_memoria(self, mensagem):
        """
        Verifica se a mensagem é uma solicitação para consultar
        as memórias da Mell.
        """

        mensagem_normalizada = (
            mensagem
            .lower()
            .strip()
            .replace("?", "")
        )

        frases = [
            "o que você lembra sobre mim",
            "o que você lembra de mim",
            "você lembra de alguma coisa sobre mim",
            "você lembra de algo sobre mim",
            "quais coisas você lembra sobre mim",
            "o que você sabe sobre mim",
        ]

        return any(
            frase in mensagem_normalizada
            for frase in frases
        )

    def _eh_pedido_esquecimento(self, mensagem):
        """
        Verifica se a mensagem indica que a Mell quer
        que alguma informação seja esquecida.
        """

        mensagem_normalizada = (
            mensagem
            .lower()
            .strip()
        )

        frases = [
            "esquece que",
            "esqueça que",
            "esquece isso",
            "esqueça isso",
            "quero que você esqueça",
            "quero que voce esqueça",
            "não quero que você lembre",
            "nao quero que voce lembre",
            "não quero que guarde",
            "nao quero que guarde",
        ]

        return any(
            frase in mensagem_normalizada
            for frase in frases
        )

    def _extrair_alvo_esquecimento(self, mensagem):
        """
        Tenta extrair o assunto que a Mell quer esquecer.

        Por enquanto usamos regras simples.
        """

        texto = (
            mensagem
            .lower()
            .strip()
        )

        marcadores = [
            "esquece que",
            "esqueça que",
            "quero que você esqueça",
            "quero que voce esqueça",
            "não quero que você lembre",
            "nao quero que voce lembre",
            "não quero que guarde",
            "nao quero que guarde",
        ]

        for marcador in marcadores:

            if marcador in texto:

                alvo = texto.split(
                    marcador,
                    1
                )[1]

                alvo = (
                    alvo
                    .strip()
                    .strip(".!?")
                )

                # Remove alguns inícios comuns
                # para facilitar a busca.

                palavras_iniciais = [
                    "eu ",
                    "que eu ",
                    "de ",
                    "sobre ",
                ]

                for inicio in palavras_iniciais:

                    if alvo.startswith(inicio):

                        alvo = alvo[
                            len(inicio):
                        ]

                return alvo.strip()

        return None
    # ============================================================
    # RESPONDER
    # ============================================================

    def gerar_texto(self, mensagem):
        """Obtém um texto da IA sem alterar o histórico de conversa."""
        if not mensagem or not mensagem.strip():
            return ""

        resposta = self.cliente.responses.create(
            model=self.modelo,
            instructions=self._criar_instrucoes(),
            input=mensagem.strip(),
            max_output_tokens=1200,
        )
        texto = resposta.output_text.strip()
        if not texto:
            raise RuntimeError("A IA retornou uma resposta vazia.")
        return texto

    def responder(self, mensagem, ao_receber=None):
        """
        Processa uma mensagem da Mell.

        Se existir uma memória aguardando autorização,
        a mensagem será interpretada primeiro como resposta
        à solicitação de memória.
        """

        if not mensagem or not mensagem.strip():
            return ""

        mensagem = mensagem.strip()

        # ========================================================
        # CONSULTA DE MEMÓRIA
        # ========================================================

        if self._eh_consulta_memoria(mensagem):

            resposta = self.obter_memorias_usuario()

            self.historico.append(
                {
                    "role": "user",
                    "content": mensagem
                }
            )

            self.historico.append(
                {
                    "role": "assistant",
                    "content": resposta
                }
            )

            return resposta

        # ========================================================
        # PEDIDO DE ESQUECIMENTO
        # ========================================================
        #
        # POR ENQUANTO:
        # Apenas detectamos a intenção.
        #
        # A lógica para descobrir qual memória deve ser esquecida
        # será adicionada na próxima etapa.
        # ========================================================

        if self._eh_pedido_esquecimento(mensagem):

            resposta = (
                "Entendi que você quer que eu esqueça alguma coisa. "
                "Ainda estou aprendendo a identificar exatamente "
                "qual memória você quer remover."
            )

            self.historico.append(
                {
                    "role": "user",
                    "content": mensagem
                }
            )

            self.historico.append(
                {
                    "role": "assistant",
                    "content": resposta
                }
            )

            return resposta

        # ========================================================
        # AUTORIZAÇÃO DE MEMÓRIA
        # ========================================================

        if self.esta_aguardando_memoria():

            decisao = (
                self.memoria_inteligente
                .interpretar_autorizacao(mensagem)
            )

            candidato = self.obter_candidato_memoria()

            acao = self.estado.obter_acao_memoria()

            # ====================================================
            # AUTORIZAÇÃO CONFIRMADA
            # ====================================================

            if decisao == "sim":

                # ------------------------------------------------
                # CRIAR NOVA MEMÓRIA
                # ------------------------------------------------

                if acao == EstadoConversa.ACAO_CRIAR:

                    memoria_salva = self.memoria.adicionar(
                        categoria=candidato["categoria"],
                        conteudo=candidato["conteudo"],
                        origem="conversa",
                        autorizada=True
                    )

                    self.estado.finalizar_autorizacao()

                    if memoria_salva:
                        resposta = (
                            "Fechado. 💜 Vou lembrar disso."
                        )
                    else:
                        resposta = (
                            "Tive um problema ao guardar isso."
                        )

                # ------------------------------------------------
                # ATUALIZAR MEMÓRIA EXISTENTE
                # ------------------------------------------------

                elif acao == EstadoConversa.ACAO_ATUALIZAR:

                    memoria_id = candidato.get(
                        "memoria_id"
                    )

                    memoria_atualizada = (
                        self.memoria.aplicar_atualizacao(
                            memoria_id,
                            candidato["conteudo"]
                        )
                    )

                    self.estado.finalizar_autorizacao()

                    if memoria_atualizada:
                        resposta = (
                            "Fechado. Atualizei o que eu "
                            "lembrava sobre isso. 💜"
                        )
                    else:
                        resposta = (
                            "Tive um problema ao atualizar "
                            "essa memória."
                        )

                # ------------------------------------------------
                # AÇÃO DESCONHECIDA
                # ------------------------------------------------

                else:

                    self.estado.finalizar_autorizacao()

                    resposta = (
                        "Não consegui identificar o que "
                        "deveria fazer com essa memória."
                    )

            # ====================================================
            # AUTORIZAÇÃO NEGADA
            # ====================================================

            elif decisao == "nao":

                self.estado.finalizar_autorizacao()

                resposta = (
                    "Beleza. Não vou guardar isso."
                )

            # ====================================================
            # AUTORIZAÇÃO INCERTA
            # ====================================================

            elif decisao == "incerto":

                resposta = (
                    "Não consegui entender se você quer "
                    "que eu guarde isso ou não."
                )

            # ====================================================
            # DECISÃO INVÁLIDA
            # ====================================================

            else:

                resposta = (
                    "Não consegui processar essa autorização."
                )

            # ====================================================
            # HISTÓRICO DA AUTORIZAÇÃO
            # ====================================================

            self.historico.append(
                {
                    "role": "user",
                    "content": mensagem
                }
            )

            self.historico.append(
                {
                    "role": "assistant",
                    "content": resposta
                }
            )

            return resposta

        # ========================================================
        # CONVERSA NORMAL
        # ========================================================

        self.historico.append(
            {
                "role": "user",
                "content": mensagem
            }
        )

        resposta = self.cliente.responses.create(
            model=self.modelo,
            instructions=self._criar_instrucoes(),
            input=self.historico[-12:],
            max_output_tokens=600,
        )

        texto_resposta = resposta.output_text

        self.historico.append(
            {
                "role": "assistant",
                "content": texto_resposta
            }
        )

        if ao_receber:
            ao_receber(texto_resposta)

        # ========================================================
        # ANÁLISE DE MEMÓRIA
        # ========================================================

        analise = (
            self.memoria_inteligente
            .analisar_com_ia(mensagem)
        )

        candidato = (
            self.memoria_inteligente
            .criar_candidato(analise)
        )

        if candidato:

            # ----------------------------------------------------
            # COMPARAR COM MEMÓRIAS EXISTENTES
            # ----------------------------------------------------

            memorias_existentes = self.memoria.listar()

            comparacao = (
                self.memoria_inteligente
                .comparar_com_memorias(
                    candidato,
                    memorias_existentes
                )
            )

            resultado = comparacao.get(
                "resultado"
            )

            # ----------------------------------------------------
            # MEMÓRIA NOVA
            # ----------------------------------------------------

            if resultado == "nova":

                self.estado.iniciar_autorizacao(
                    candidato,
                    EstadoConversa.ACAO_CRIAR
                )

            # ----------------------------------------------------
            # MEMÓRIA DUPLICADA
            # ----------------------------------------------------

            elif resultado == "duplicada":

                pass

            # ----------------------------------------------------
            # ATUALIZAÇÃO DE MEMÓRIA
            # ----------------------------------------------------

            elif resultado == "atualizacao":

                memoria_id = comparacao.get(
                    "memoria_id"
                )

                if memoria_id:

                    candidato["memoria_id"] = memoria_id

                    self.estado.iniciar_autorizacao(
                        candidato,
                        EstadoConversa.ACAO_ATUALIZAR
                    )

        return texto_resposta

    # ============================================================
    # MÉTODOS DE CONTROLE DA MEMÓRIA
    # ============================================================

    def obter_candidato_memoria(self):
        """Retorna o candidato atual, se existir."""

        return self.estado.obter_candidato()

    def esta_aguardando_memoria(self):
        """Verifica se a Lyra está aguardando autorização."""

        return self.estado.aguardando_autorizacao()

    def obter_memorias_usuario(self):
        """
        Retorna as memórias ativas da Mell organizadas
        para serem apresentadas de forma legível.
        """

        memorias = self.memoria.listar()

        if not memorias:
            return (
                "Ainda não tenho memórias permanentes "
                "sobre você."
            )

        categorias = {}

        for memoria in memorias:

            categoria = memoria.get(
                "categoria",
                "outros"
            )

            conteudo = memoria.get(
                "conteudo",
                ""
            )

            if not conteudo:
                continue

            if categoria not in categorias:
                categorias[categoria] = []

            categorias[categoria].append(
                conteudo
            )

        linhas = [
            "Estas são as coisas que lembro sobre você:"
        ]

        for categoria, itens in categorias.items():

            linhas.append(
                f"\n{categoria.upper()}:"
            )

            for item in itens:

                linhas.append(
                    f"- {item}"
                )

        return "\n".join(linhas)

    # ============================================================
    # HISTÓRICO
    # ============================================================

    def limpar_historico(self):
        """Apaga o histórico da conversa atual."""

        self.historico.clear()
