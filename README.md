# LYRA Web

Site da LYRA com visão geral, planejamento, agenda e conversa, inspirado em *A Noite Estrelada*. A interface pública roda no GitHub Pages; o núcleo Python pode ser hospedado como uma API separada.

## Abrir localmente

Na pasta principal do projeto, execute pelo PowerShell:

```powershell
.\projetoLYRA\.venv\Scripts\python.exe .\web\server.py
```

Depois, acesse `http://127.0.0.1:8000`. O servidor local usa o núcleo Python e os dados do aplicativo desktop.

## Integração online

O site publicado usa o backend configurado em `api-config.js`. O arquivo `render.yaml` descreve um serviço Render gratuito para testes. Para criá-lo:

1. No Render, escolha **New → Blueprint** e conecte o repositório `Mellissa-Spinelli/Lyra_site`.
2. No formulário de configuração, informe `OPENAI_API_KEY` e crie uma senha longa para `LYRA_ACCESS_PASSWORD` (mínimo de 12 caracteres). O Render gera `LYRA_SESSION_SECRET` automaticamente.
3. Após o serviço iniciar, o site apresenta o botão **Conectar**. A conversa e a geração de planejamento passam pelo backend autenticado.

O endereço esperado da API está em `api-config.js`. Se o Render atribuir outro subdomínio, atualize esse arquivo e envie a alteração para `main`.

### Limites atuais

- A agenda online fica no armazenamento local do navegador. No servidor local, ela continua usando `projetoLYRA/agenda_lyra.json`.
- A memória da IA hospedada fica em armazenamento temporário do serviço e pode ser apagada quando ele reiniciar ou for atualizado.
- A configuração de teste não inclui banco de dados persistente.
- O código do núcleo e os prompts da LYRA ficam no repositório público; arquivos `.env`, chaves de API, memórias existentes e a agenda local não são publicados.
- No Render, o plano gratuito pode suspender o serviço quando não está em uso; a primeira chamada após a suspensão pode demorar.

## Publicação do site

O workflow em `.github/workflows/pages.yml` publica somente os arquivos da interface (`index.html`, `styles.css`, `app.js` e `api-config.js`). Cada envio para `main` atualiza o GitHub Pages. O endereço é https://mellissa-spinelli.github.io/Lyra_site/.
