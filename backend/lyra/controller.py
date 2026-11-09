from .ia import LyraIA


class LyraController:
    """Adapta as solicitações da interface para os serviços da LYRA."""

    def __init__(self):
        """Cria o controlador que conecta a interface ao núcleo da LYRA."""
        self.lyra = LyraIA()

    # =====================================================
    # CHAT
    # =====================================================

    def enviar(self, mensagem, ao_receber=None):
        """Envia uma mensagem do chat com instruções para resposta concisa."""

        if not mensagem or not mensagem.strip():
            return ""

        prompt = (
            "[MODO CHAT GRÁFICO]\n"
            "Responda de forma curta e natural, adequada para "
            "uma caixa de diálogo. "
            "Prefira respostas de 1 a 3 frases. "
            "Evite textos longos, listas extensas ou explicações "
            "detalhadas, a menos que a usuária peça explicitamente "
            "por mais detalhes.\n\n"
            f"Mensagem da usuária:\n{mensagem.strip()}"
        )

        return self.lyra.responder(prompt, ao_receber=ao_receber)

    # =====================================================
    # PLANEJAMENTO DE METODOLOGIA
    # =====================================================

    def gerar_metodologia(
        self,
        conteudo,
        metodologias
    ):
        """Solicita uma metodologia de aula com base nos dados selecionados."""

        if not conteudo or not conteudo.strip():
            return ""

        if not metodologias:
            return ""

        # -------------------------------------------------
        # Organiza as metodologias selecionadas
        # -------------------------------------------------

        lista_metodologias = []

        for metodologia in metodologias:

            if isinstance(metodologia, dict):

                nome = metodologia.get(
                    "nome",
                    ""
                ).strip()

                descricao = metodologia.get(
                    "descricao",
                    ""
                ).strip()

                if descricao:

                    lista_metodologias.append(
                        f"- {nome}: {descricao}"
                    )

                else:

                    lista_metodologias.append(
                        f"- {nome}"
                    )

            else:

                lista_metodologias.append(
                    f"- {str(metodologia).strip()}"
                )

        metodologias_texto = "\n".join(
            lista_metodologias
        )

        # -------------------------------------------------
        # Prompt específico do Planejamento
        # -------------------------------------------------

        prompt = (
            "[MODO PLANEJAMENTO DE METODOLOGIA]\n\n"

            "Você está auxiliando uma professora na elaboração "
            "de planejamentos escolares.\n\n"

            "CONTEÚDO OU HABILIDADE DA AULA:\n"
            f"{conteudo.strip()}\n\n"

            "METODOLOGIAS SELECIONADAS:\n"
            f"{metodologias_texto}\n\n"

            "TAREFA:\n"
            "Elabore uma metodologia de aula coerente com o "
            "conteúdo ou habilidade informado e com as "
            "metodologias selecionadas.\n\n"

            "REGRAS:\n"
            "- Escreva um texto objetivo, pedagógico e adequado para "
            "um planejamento de aula futura.\n"
            "- Utilize predominantemente verbos no futuro ou construções "
            "que indiquem ações que serão realizadas durante a aula.\n"
            "- Evite descrever a aula como se ela já tivesse acontecido.\n"
            "- Não utilize construções no passado ou no presente que "
            "indiquem ações já realizadas.\n"
            "- Prefira construções como: 'será realizada', "
            "'serão apresentados', 'os estudantes irão analisar', "
            "'o professor irá orientar', 'ao final, será realizada'.\n"
            "- Integre naturalmente as metodologias selecionadas "
            "ao desenvolvimento da aula.\n"
            "- Não apenas liste as metodologias.\n"
            "- Explique brevemente como elas serão utilizadas.\n"
            "- O texto deve estar pronto para ser inserido "
            "diretamente em um planejamento escolar.\n"
            "- Não faça introduções ou comentários sobre o texto.\n"
            "- Não use tópicos ou listas.\n"
            "- Entregue somente o texto final da metodologia.\n"
            "- Mantenha o texto entre 80 e 150 palavras, priorizando "
            "clareza e objetividade.\n"
            "- Descreva apenas as principais etapas da aula, sem "
            "detalhar excessivamente perguntas, papéis dos grupos, "
            "materiais ou atividades específicas.\n"
        )

        return self.lyra.gerar_texto(prompt)
