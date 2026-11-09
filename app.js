const pages = {
  inicio: "Visão geral",
  planejamento: "Planejamento",
  agenda: "Agenda",
  conversa: "Conversar com Lyra",
  temas: "Temas",
};

const navButtons = [...document.querySelectorAll(".nav-link")];
const pageSections = [...document.querySelectorAll(".page")];
const pageLabel = document.getElementById("page-label");
const previewStorageKey = "lyra-preview-agenda-v2";
const themeStorageKey = "lyra-selected-theme-v1";
const apiBaseUrl = (window.LYRA_CONFIG?.apiBaseUrl || "").replace(/\/+$/, "");
const remoteMode = Boolean(apiBaseUrl);
const authStorageKey = "lyra-api-session-v1";
let authToken = remoteMode ? sessionStorage.getItem(authStorageKey) || "" : "";
let apiAvailable = false;

const themes = {
  "starry-night": {
    name: "A Noite Estrelada",
    description: "Azuis profundos, redemoinhos celestes e pontos de luz dourada.",
    caption: "NOITE ESTRELADA · VAN GOGH",
    browserColor: "#101d3c",
  },
  "monet-sunrise": {
    name: "Impressão, nascer do sol",
    description: "Névoa azul-acinzentada, água verde-petróleo e um sol coral.",
    caption: "IMPRESSÃO, NASCER DO SOL · MONET",
    browserColor: "#536f74",
  },
  "monet-nympheas": {
    name: "O lago das ninfeias",
    description: "Verdes de jardim, reflexos azulados e flores em rosa suave.",
    caption: "NYMPHÉAS · MONET",
    browserColor: "#294a49",
  },
};

function applyTheme(themeId, save = true) {
  const selectedTheme = themes[themeId] ? themeId : "starry-night";
  const theme = themes[selectedTheme];
  document.body.dataset.theme = selectedTheme;
  document.getElementById("active-theme-name").textContent = theme.name;
  document.getElementById("active-theme-description").textContent = theme.description;
  document.getElementById("hero-art-caption").textContent = theme.caption;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme.browserColor);
  document.querySelectorAll("[data-theme-card]").forEach((card) => {
    const active = card.dataset.themeCard === selectedTheme;
    card.classList.toggle("is-selected", active);
    const button = card.querySelector("[data-theme-select]");
    button.setAttribute("aria-pressed", String(active));
    button.replaceChildren(document.createTextNode(active ? "Tema aplicado ✓" : "Aplicar tema"));
    if (!active) {
      const arrow = document.createElement("span");
      arrow.textContent = "↗";
      button.append(arrow);
    }
  });
  if (save) {
    try { localStorage.setItem(themeStorageKey, selectedTheme); } catch { /* Preferências podem estar desativadas no navegador. */ }
  }
}

let savedTheme = "starry-night";
try {
  const storedTheme = localStorage.getItem(themeStorageKey);
  if (themes[storedTheme]) savedTheme = storedTheme;
} catch { /* Usa o tema inicial se o navegador bloquear armazenamento local. */ }
applyTheme(savedTheme, false);
document.querySelectorAll("[data-theme-select]").forEach((button) => {
  button.addEventListener("click", () => applyTheme(button.dataset.themeSelect));
});

function setApiMode(connected) {
  apiAvailable = connected;
  document.getElementById("mode-label").textContent = connected ? (remoteMode ? "Backend LYRA conectado" : "Núcleo LYRA conectado") : "Modo de prévia";
  document.getElementById("chat-mode").textContent = connected ? "IA CONECTADA" : "MODO DE PRÉVIA";
  document.getElementById("chat-disclaimer").textContent = connected
    ? "As mensagens seguem para o backend protegido da LYRA. A chave da API fica no servidor."
    : "Nesta prévia, as respostas são demonstrativas. As mensagens não saem deste navegador.";
  const connectionButton = document.getElementById("backend-login");
  connectionButton.hidden = !remoteMode;
  connectionButton.textContent = connected ? "Desconectar" : "Conectar";
}

function openPage(name) {
  if (!pages[name]) return;
  pageSections.forEach((page) => page.classList.toggle("active", page.id === `page-${name}`));
  navButtons.forEach((button) => button.classList.toggle("active", button.dataset.page === name));
  pageLabel.textContent = pages[name];
  window.scrollTo({ top: 0, behavior: "smooth" });
}

navButtons.forEach((button) => button.addEventListener("click", () => openPage(button.dataset.page)));
document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => openPage(button.dataset.go)));

const now = new Date();
document.getElementById("today-label").textContent = new Intl.DateTimeFormat("pt-BR", {
  weekday: "long", day: "numeric", month: "long",
}).format(now);

async function apiRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (remoteMode && authToken) headers.Authorization = `Bearer ${authToken}`;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Não consegui concluir essa ação.");
  return data;
}

const connectionDialog = document.getElementById("connection-dialog");
const connectionForm = document.getElementById("connection-form");
const connectionPassword = document.getElementById("connection-password");
const connectionError = document.getElementById("connection-error");

document.getElementById("backend-login").addEventListener("click", async () => {
  if (apiAvailable && remoteMode) {
    authToken = "";
    sessionStorage.removeItem(authStorageKey);
    setApiMode(false);
    await Promise.all([loadMethods(), loadAgenda()]);
    return;
  }
  connectionError.hidden = true;
  connectionDialog.showModal();
  connectionPassword.focus();
});

document.getElementById("connection-close").addEventListener("click", () => connectionDialog.close());
connectionDialog.addEventListener("click", (event) => {
  if (event.target === connectionDialog) connectionDialog.close();
});

connectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = document.getElementById("connection-submit");
  const password = connectionPassword.value;
  submit.disabled = true;
  connectionError.hidden = true;
  try {
    const data = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    authToken = data.token;
    sessionStorage.setItem(authStorageKey, authToken);
    connectionPassword.value = "";
    connectionDialog.close();
    await initializeSite();
  } catch (error) {
    connectionError.textContent = error.message;
    connectionError.hidden = false;
  } finally {
    submit.disabled = false;
  }
});

const plannerForm = document.getElementById("planner-form");
const draftPlaceholder = document.getElementById("draft-placeholder");
const draftResult = document.getElementById("draft-result");
const draftText = document.getElementById("draft-text");
const methodList = document.getElementById("method-list");
let currentDraft = "";
const previewMethods = [
  "Aula expositiva dialogada", "Debate", "Análise de imagens", "Análise de mapas",
  "Estudo de caso", "Atividade impressa", "Trabalho em grupo", "Pesquisa",
  "Vídeo", "Mapa mental", "Análise de texto", "Resolução de questões",
];

function renderMethods(methods) {
  methodList.replaceChildren();
  methods.forEach((method, index) => {
    const label = document.createElement("label");
    label.className = "method-chip";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = typeof method === "string" ? method : method.nome;
    input.checked = index === 0;
    const name = document.createElement("span");
    name.textContent = input.value;
    label.append(input, name);
    methodList.append(label);
  });
}

async function loadMethods() {
  if (!apiAvailable && !remoteMode) {
    renderMethods(previewMethods);
    return;
  }
  try {
    const data = await apiRequest("/api/metodologias");
    renderMethods(data.metodologias);
  } catch {
    setApiMode(false);
    renderMethods(previewMethods);
  }
}

function makePreviewDraft(topic, audience, methods) {
  const turma = audience ? ` Considerando a turma ${audience},` : "";
  const abordagem = methods.length ? methods.join(", ").toLowerCase() : "exploração guiada do tema";
  return `A aula começará com uma conversa breve para identificar o que os estudantes já sabem sobre ${topic.toLowerCase()}. Em seguida, a turma será convidada a explorar o conteúdo por meio de ${abordagem}, registrando perguntas e observações. ${turma} o desenvolvimento será conduzido em etapas curtas, com espaço para compartilhar descobertas e construir relações com situações do cotidiano. Para encerrar, cada estudante poderá sintetizar uma aprendizagem e uma curiosidade que ainda deseja investigar.`;
}

plannerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const topic = document.getElementById("lesson-topic").value.trim();
  const audience = document.getElementById("lesson-audience").value.trim();
  const methods = [...plannerForm.querySelectorAll("input[type=checkbox]:checked")].map((input) => input.value);
  if (!topic) {
    document.getElementById("lesson-topic").focus();
    return;
  }
  draftPlaceholder.hidden = true;
  draftResult.hidden = false;
  draftText.textContent = "A LYRA está pensando em uma proposta para sua aula…";
  const submit = plannerForm.querySelector("button[type=submit]");
  submit.disabled = true;
  try {
    if (apiAvailable) {
      const data = await apiRequest("/api/planejamento", {
        method: "POST",
        body: JSON.stringify({ content: topic, audience, methods }),
      });
      currentDraft = data.response;
    } else {
      currentDraft = makePreviewDraft(topic, audience, methods);
    }
    document.getElementById("draft-title").textContent = topic;
    draftText.textContent = currentDraft;
    const methodsContainer = document.getElementById("draft-methods");
    methodsContainer.replaceChildren();
    methods.forEach((method) => {
      const tag = document.createElement("span");
      tag.textContent = method;
      methodsContainer.append(tag);
    });
  } catch (error) {
    setApiMode(false);
    currentDraft = makePreviewDraft(topic, audience, methods);
    document.getElementById("draft-title").textContent = topic;
    draftText.textContent = `${currentDraft}\n\n(A prévia local foi usada porque não consegui falar com o núcleo de IA.)`;
    const methodsContainer = document.getElementById("draft-methods");
    methodsContainer.replaceChildren();
    methods.forEach((method) => {
      const tag = document.createElement("span");
      tag.textContent = method;
      methodsContainer.append(tag);
    });
  } finally {
    submit.disabled = false;
  }
});

document.getElementById("copy-draft").addEventListener("click", async () => {
  if (!currentDraft) return;
  try {
    await navigator.clipboard.writeText(currentDraft);
    const button = document.getElementById("copy-draft");
    button.textContent = "✓";
    window.setTimeout(() => { button.textContent = "▢"; }, 1400);
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(draftText);
    selection.removeAllRanges();
    selection.addRange(range);
  }
});

const agendaForm = document.getElementById("agenda-form");
const agendaList = document.getElementById("agenda-list");
const agendaEmpty = document.getElementById("agenda-empty");
const agendaCount = document.getElementById("agenda-count");
const weekDays = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
let agendaItems = [];

function readPreviewAgenda() {
  try {
    const items = JSON.parse(localStorage.getItem(previewStorageKey) || "[]");
    return Array.isArray(items) ? items.filter((item) => Number.isInteger(item.dia) && item.disciplina) : [];
  } catch {
    return [];
  }
}

function savePreviewAgenda() {
  localStorage.setItem(previewStorageKey, JSON.stringify(agendaItems));
}

function renderAgenda() {
  agendaList.replaceChildren();
  agendaEmpty.hidden = agendaItems.length > 0;
  agendaCount.textContent = `${agendaItems.length} ${agendaItems.length === 1 ? "aula" : "aulas"}`;

  agendaItems.forEach((item) => {
    const entry = document.createElement("article");
    entry.className = "agenda-item";
    const day = document.createElement("div");
    day.className = "agenda-day";
    const dayName = document.createElement("strong");
    dayName.textContent = weekDays[item.dia].slice(0, 3).toUpperCase();
    const dayNumber = document.createElement("small");
    dayNumber.textContent = `DIA ${item.dia + 1}`;
    day.append(dayName, dayNumber);

    const copy = document.createElement("div");
    copy.className = "agenda-copy";
    const title = document.createElement("strong");
    title.textContent = item.disciplina;
    copy.append(title);
    if (item.horario_exibicao || item.horario) {
      const time = document.createElement("p");
      time.className = "agenda-time";
      time.textContent = item.horario_exibicao || item.horario;
      copy.append(time);
    }
    if (item.resumo) {
      const note = document.createElement("p");
      note.textContent = item.resumo;
      copy.append(note);
    }

    const remove = document.createElement("button");
    remove.className = "agenda-delete";
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", `Remover ${item.disciplina} de ${weekDays[item.dia]}`);
    remove.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        if (apiAvailable && !remoteMode) {
          await apiRequest(`/api/agenda/${encodeURIComponent(item.id)}`, { method: "DELETE" });
          await loadAgenda();
        } else {
          agendaItems = agendaItems.filter((entryItem) => entryItem.id !== item.id);
          savePreviewAgenda();
          renderAgenda();
        }
      } catch (error) {
        setApiMode(false);
        agendaItems = agendaItems.filter((entryItem) => entryItem.id !== item.id);
        savePreviewAgenda();
        renderAgenda();
        remove.disabled = false;
      }
    });
    entry.append(day, copy, remove);
    agendaList.append(entry);
  });
}

async function loadAgenda() {
  if (!apiAvailable || remoteMode) {
    agendaItems = readPreviewAgenda();
    agendaItems.sort((a, b) => a.dia - b.dia || (a.ordem || 0) - (b.ordem || 0));
    renderAgenda();
    return;
  }
  try {
    const data = await apiRequest("/api/agenda");
    agendaItems = data.aulas;
    agendaItems.sort((a, b) => a.dia - b.dia || (a.ordem || 0) - (b.ordem || 0) || (a.horario || "").localeCompare(b.horario || ""));
    renderAgenda();
  } catch (error) {
    setApiMode(false);
    agendaItems = readPreviewAgenda();
    agendaItems.sort((a, b) => a.dia - b.dia || (a.ordem || 0) - (b.ordem || 0));
    renderAgenda();
  }
}

agendaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = agendaForm.querySelector("button[type=submit]");
  submit.disabled = true;
  const item = {
    id: `preview-${Date.now()}`,
    dia: Number(document.getElementById("agenda-day").value),
    horario: document.getElementById("agenda-time").value.trim(),
    disciplina: document.getElementById("agenda-discipline").value.trim(),
    resumo: document.getElementById("agenda-summary").value.trim(),
    materiais: document.getElementById("agenda-materials").value.trim(),
  };
  try {
    if (apiAvailable && !remoteMode) {
      await apiRequest("/api/agenda", {
        method: "POST",
        body: JSON.stringify({ day: item.dia, time: item.horario, discipline: item.disciplina, summary: item.resumo, materials: item.materiais }),
      });
    } else {
      agendaItems.push(item);
      savePreviewAgenda();
    }
    agendaForm.reset();
    await loadAgenda();
  } catch (error) {
    setApiMode(false);
    agendaItems = readPreviewAgenda();
    agendaItems.push(item);
    savePreviewAgenda();
    agendaForm.reset();
    await loadAgenda();
  } finally {
    submit.disabled = false;
  }
});

loadAgenda();

const chatStream = document.getElementById("chat-stream");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const suggestions = [...document.querySelectorAll(".suggestions button")];
const previewReplies = [
  "Uma boa abertura pode começar com uma imagem, um objeto ou uma pergunta curiosa ligada ao tema. Convide a turma a compartilhar hipóteses e retome essas ideias durante a aula.",
  "Podemos construir essa explicação em passos pequenos, começando por algo que a turma já conhece. Qual é o tema e para qual faixa etária você está planejando?",
  "Vamos organizar essa ideia com calma. O que você gostaria que os estudantes levassem dessa aula ao final?",
];

function appendMessage(author, text) {
  const message = document.createElement("div");
  const isUser = author === "VOCÊ";
  message.className = `message ${isUser ? "user-message" : "lyra-message"}`;
  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.textContent = isUser ? "✦" : "✧";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const meta = document.createElement("small");
  meta.textContent = `${author} · agora`;
  const body = document.createElement("p");
  body.textContent = text;
  bubble.append(meta, body);
  message.append(avatar, bubble);
  chatStream.append(message);
  chatStream.scrollTop = chatStream.scrollHeight;
}

async function sendChatMessage(text) {
  const message = text.trim();
  if (!message) return;
  appendMessage("VOCÊ", message);
  chatInput.value = "";
  suggestions.forEach((button) => { button.hidden = true; });
  const pending = document.createElement("div");
  pending.className = "message lyra-message";
  pending.dataset.pending = "true";
  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.textContent = "✧";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const meta = document.createElement("small");
  meta.textContent = "LYRA · agora";
  const body = document.createElement("p");
  body.textContent = "Pensando junto...";
  bubble.append(meta, body);
  pending.append(avatar, bubble);
  chatStream.append(pending);
  chatStream.scrollTop = chatStream.scrollHeight;
  if (!apiAvailable) {
    if (remoteMode) {
      pending.remove();
      appendMessage("LYRA", "Para conversar com o núcleo real, conecte-se pelo botão no topo da página.");
      return;
    }
    window.setTimeout(() => {
      pending.remove();
      const responseIndex = message.toLocaleLowerCase("pt-BR").includes("simples") ? 1
        : message.toLocaleLowerCase("pt-BR").includes("aula") ? 2 : 0;
      appendMessage("LYRA", previewReplies[responseIndex]);
    }, 650);
    return;
  }
  try {
    const data = await apiRequest("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    pending.remove();
    appendMessage("LYRA", data.response);
  } catch (error) {
    setApiMode(false);
    pending.remove();
    appendMessage("LYRA", remoteMode ? `Não consegui falar com o backend agora. ${error.message}` : previewReplies[0]);
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendChatMessage(chatInput.value);
});
suggestions.forEach((button) => button.addEventListener("click", () => sendChatMessage(button.dataset.prompt)));

async function initializeSite() {
  if (remoteMode) {
    let connected = false;
    if (authToken) {
      try {
        await apiRequest("/api/auth/me");
        connected = true;
      } catch (error) {
        if (error.message.includes("Conecte-se")) {
          authToken = "";
          sessionStorage.removeItem(authStorageKey);
        }
      }
    }
    setApiMode(connected);
    await Promise.all([loadMethods(), loadAgenda()]);
    return;
  }
  try {
    await apiRequest("/api/status");
    setApiMode(true);
  } catch {
    setApiMode(false);
  }
  await Promise.all([loadMethods(), loadAgenda()]);
}

initializeSite();
