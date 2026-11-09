# LYRA Web — primeira versão

Site da LYRA com visão geral, planejamento, agenda e conversa. A publicação no GitHub Pages usa o modo de prévia, com respostas de demonstração e dados guardados no navegador. O servidor Python conecta a versão local ao núcleo de IA e aos dados existentes do aplicativo desktop.

## Abrir localmente

Na pasta principal do projeto, execute pelo PowerShell:

```powershell
.\projetoLYRA\.venv\Scripts\python.exe .\web\server.py
```

Depois, acesse `http://127.0.0.1:8000` no navegador. Para encerrar, use `Ctrl+C` no terminal.

## O que funciona nesta versão

- Navegação entre as quatro áreas da LYRA.
- Em GitHub Pages, as quatro áreas podem ser exploradas sem backend; a agenda de demonstração fica no navegador.
- No servidor local, chat e geração de metodologia usam o núcleo Python e a API configurada no projeto.
- No servidor local, metodologias vêm de `projetoLYRA/metodologias.json` e a grade semanal é salva em `projetoLYRA/agenda_lyra.json`.
- Layout responsivo para celular e computador.

## GitHub Pages

O workflow em `.github/workflows/pages.yml` publica apenas `index.html`, `styles.css` e `app.js`. No repositório, abra **Settings → Pages** e selecione **GitHub Actions** como fonte. A cada envio para `main`, o site será atualizado. O endereço publicado é público; nenhum arquivo `.env`, agenda local ou backend Python é enviado pelo workflow.

O servidor local escuta somente em `127.0.0.1`. Para uma versão online com IA real e dados sincronizados, será necessário hospedar também o backend Python em um serviço próprio.
