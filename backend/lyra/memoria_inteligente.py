"""
MEMÓRIA INTELIGENTE DA LYRA

Responsável por analisar informações que aparecem durante
as conversas e determinar como elas devem ser tratadas.

A análise semântica é feita pela IA.
O armazenamento continua sendo responsabilidade de memoria.py.
"""

import json


class MemoriaInteligente:
    """Analisa informações para determinar se devem virar memória."""

    CATEGORIAS_VALIDAS = [
        "fatos",
        "preferencias",
        "projetos",
        "objetivos",
        "rotina",
        "relacoes",
        "memorias_sociais",
        "padroes",
    ]

    def __init__(self, cliente, modelo="gpt-5-mini"):
        """Configura o cliente e o modelo usados na análise de memória."""
        self.cliente = cliente
        self.modelo = modelo

    def analisar_com_ia(self, mensagem):
        """
        Analisa uma mensagem usando a IA.

        Retorna um dicionário estruturado com:
        - memoravel
        - categoria
        - conteudo
        - importancia
        - acao
        """

        if not mensagem or not mensagem.strip():
            return {
                "memoravel": False,
                "categoria": None,
                "conteudo": None,
                "importancia": "baixa",
                "acao": "ignorar",
            }

        instrucoes = f"""
Você é o sistema de análise de memória da Lyra.

Sua função NÃO é responder à usuária.

Sua função é analisar uma mensagem e determinar se existe nela
alguma informação que possa ser útil como memória permanente
sobre Mell.

CATEGORIAS PERMITIDAS:

- fatos
- preferencias
- projetos
- objetivos
- rotina
- relacoes
- memorias_sociais
- padroes

REGRAS:

1. Não considere informações triviais ou passageiras como memórias.

2. Não transforme estados temporários em características permanentes.

3. Não trate inferências como fatos.

4. Não crie informações que não estejam presentes na mensagem.

5. Preferências, objetivos, projetos, relações e fatos pessoais
   potencialmente úteis podem ser considerados memoráveis.

6. Padrões de comportamento exigem cautela. Uma única mensagem
   normalmente não é suficiente para estabelecer um padrão.

7. Se houver dúvida, prefira NÃO memorizar.

8. A ação deve ser uma destas:

   - "ignorar"
   - "confirmar"

9. A análise deve ser retornada SOMENTE como JSON válido.

FORMATO OBRIGATÓRIO:

{{
    "memoravel": true ou false,
    "categoria": "categoria válida ou null",
    "conteudo": "informação resumida de forma objetiva ou null",
    "importancia": "baixa", "media" ou "alta",
    "acao": "ignorar" ou "confirmar"
}}
"""

        resposta = self.cliente.responses.create(
            model=self.modelo,
            instructions=instrucoes,
            input=mensagem.strip(),
            max_output_tokens=160,
        )

        texto = resposta.output_text.strip()

        try:
            resultado = json.loads(texto)

        except json.JSONDecodeError:
            return {
                "memoravel": False,
                "categoria": None,
                "conteudo": None,
                "importancia": "baixa",
                "acao": "ignorar",
            }

        return self._validar_resultado(resultado)

    def _validar_resultado(self, resultado):
        """Garante que a resposta da IA siga nossas regras."""

        if not isinstance(resultado, dict):
            return {
                "memoravel": False,
                "categoria": None,
                "conteudo": None,
                "importancia": "baixa",
                "acao": "ignorar",
            }

        memoravel = resultado.get("memoravel") is True
        categoria = resultado.get("categoria")
        conteudo = resultado.get("conteudo")
        importancia = resultado.get("importancia", "baixa")
        acao = resultado.get("acao", "ignorar")

        if categoria not in self.CATEGORIAS_VALIDAS:
            categoria = None

        if importancia not in ["baixa", "media", "alta"]:
            importancia = "baixa"

        if acao not in ["ignorar", "confirmar"]:
            acao = "ignorar"

        if not memoravel:
            categoria = None
            conteudo = None
            acao = "ignorar"

        if not isinstance(conteudo, str) or not conteudo.strip():
            memoravel = False
            categoria = None
            conteudo = None
            acao = "ignorar"

        return {
            "memoravel": memoravel,
            "categoria": categoria,
            "conteudo": conteudo,
            "importancia": importancia,
            "acao": acao,
        }

    def criar_candidato(self, resultado):
        """
        Cria um candidato a memória a partir de uma análise.

        O candidato ainda NÃO é salvo na memória permanente.
        """

        if not resultado:
            return None

        if not resultado.get("memoravel"):
            return None

        if resultado.get("acao") != "confirmar":
            return None

        categoria = resultado.get("categoria")
        conteudo = resultado.get("conteudo")

        if not categoria or not conteudo:
            return None

        return {
            "categoria": categoria,
            "conteudo": conteudo,
            "importancia": resultado.get(
                "importancia",
                "media"
            ),
            "status": "aguardando_confirmacao"
        }

    def interpretar_autorizacao(self, mensagem):
        """
        Analisa uma resposta da Mell quando existe uma memória
        aguardando autorização.

        Retorna:
        - "sim"
        - "nao"
        - "incerto"
        """

        if not mensagem or not mensagem.strip():
            return "incerto"

        instrucoes = """
Você é um sistema de interpretação de autorização de memória.

A usuária está respondendo a uma pergunta sobre se uma determinada
informação pode ser armazenada como memória permanente.

Determine a intenção da resposta.

Retorne SOMENTE uma destas três palavras:

sim
nao
incerto

REGRAS:

- "sim" significa que a usuária autorizou claramente o armazenamento.
- "nao" significa que a usuária recusou claramente.
- "incerto" significa que não é possível determinar com segurança.

Exemplos de SIM:

"sim"
"pode"
"pode guardar"
"claro"
"sim, quero"
"pode lembrar disso"

Exemplos de NÃO:

"não"
"não quero"
"não precisa"
"melhor não"
"prefiro que não"

Se houver qualquer dúvida, responda "incerto".
"""

        resposta = self.cliente.responses.create(
            model=self.modelo,
            instructions=instrucoes,
            input=mensagem.strip(),
            max_output_tokens=8,
        )

        resultado = resposta.output_text.strip().lower()

        if resultado not in ["sim", "nao", "incerto"]:
            return "incerto"

        return resultado

    def comparar_com_memorias(self, candidato, memorias):
        """Classifica uma memória como nova, duplicada ou atualização."""
        if not candidato or not memorias:
            return {"resultado": "nova", "memoria_id": None}

        lista_memorias = [
            {
                "id": memoria.get("id"),
                "categoria": memoria.get("categoria"),
                "conteudo": memoria.get("conteudo"),
            }
            for memoria in memorias
        ]

        instrucoes = f"""
    Você é o sistema de gerenciamento de memória da Lyra.

    Sua tarefa é comparar uma nova informação com memórias
    permanentes que já existem.

    NOVA INFORMAÇÃO:

    Categoria:
    {candidato.get("categoria")}

    Conteúdo:
    {candidato.get("conteudo")}

    MEMÓRIAS EXISTENTES:

    {lista_memorias}

    Determine se a nova informação é:

    1. "nova"
       Não existe uma memória equivalente.

    2. "duplicada"
       Já existe uma memória que representa essencialmente
       a mesma informação.

    3. "atualizacao"
       Existe uma memória sobre o mesmo assunto, mas a nova
       informação acrescenta ou modifica algo relevante.

    REGRAS:

    - Não considere apenas palavras parecidas.
    - Compare o significado.
    - Não invente informações.
    - Se houver dúvida, prefira "nova".
    - Se for duplicada ou atualização, informe o ID da memória
      correspondente.
    - Se for nova, memoria_id deve ser null.

    Retorne SOMENTE JSON válido.

    FORMATO:

    {{
        "resultado": "nova" | "duplicada" | "atualizacao",
        "memoria_id": "ID ou null"
    }}
    """

        resposta = self.cliente.responses.create(
            model=self.modelo,
            instructions=instrucoes,
            input="Faça a comparação.",
            max_output_tokens=80,
        )

        texto = resposta.output_text.strip()

        try:
            resultado = json.loads(texto)

        except json.JSONDecodeError:
            return {"resultado": "nova", "memoria_id": None}

        if not isinstance(resultado, dict):
            return {"resultado": "nova", "memoria_id": None}

        tipo = resultado.get("resultado")
        if tipo not in {"nova", "duplicada", "atualizacao"}:
            tipo = "nova"

        memoria_id = resultado.get("memoria_id")

        if tipo == "nova":
            memoria_id = None

        return {"resultado": tipo, "memoria_id": memoria_id}
