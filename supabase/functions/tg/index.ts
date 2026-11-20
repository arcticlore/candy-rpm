// candy-rpm: Telegram-бот как Supabase Edge Function (Deno), 24/7, без cron.
//
// Почему не GitHub Actions: long-poll в tools/tg-notify.py живёт ровно столько,
// сколько длится джоба, и между запусками бот молчит. Здесь Telegram сам
// стучится в функцию на каждое сообщение.
//
// Почему не Vercel: тот же код лежит в vercel/api/telegram.py, но деплой туда
// требует привязки GitHub-аккаунта к Vercel (Login Connection), которой у
// аккаунта нет. Логика здесь — построчный порт питоновской версии; если
// появится привязка, можно вернуться на Vercel без изменения поведения.
//
// Переменные окружения (Project Settings → Edge Functions → Secrets):
//   TG_BOT_TOKEN  — токен бота (обязательно)
//   TG_SECRET     — секрет вебхука, он же X-Telegram-Bot-Api-Secret-Token
//   TG_OWNER_CHAT — chat_id владельцев через запятую/пробел/точку с запятой
//   GH_REPO       — owner/repo, по умолчанию arcticlore/candy-rpm
//   GH_TOKEN      — PAT с actions:write (нужен только для /run)
//   COPR_OWNER    — по умолчанию arcticlore
//   COPR_PROJECT  — по умолчанию candy

const GH_API = "https://api.github.com";
const COPR_API = "https://copr.fedorainfracloud.org/api_3";
const TIMEOUT = 8000;
const LIMIT = 3800; // лимит Telegram на сообщение — 4096

function env(name: string, fallback = ""): string {
  return Deno.env.get(name) ?? fallback;
}

function repo(): string {
  return env("GH_REPO", "arcticlore/candy-rpm");
}

/** TG_OWNER_CHAT → множество chat_id. Владельцев может быть несколько. */
function ownerChats(): Set<string> {
  return new Set(
    env("TG_OWNER_CHAT").trim().split(/[,\s;]+/).filter((s) => s.length > 0),
  );
}

/** Fail-closed: пустой TG_OWNER_CHAT означает «владельцев нет». */
function isOwner(chatId: unknown): boolean {
  const owners = ownerChats();
  return owners.size > 0 && owners.has(String(chatId));
}

async function getJson(url: string, headers: Record<string, string> = {}) {
  const resp = await fetch(url, {
    headers: { "User-Agent": "candy-rpm-tg-webhook", ...headers },
    signal: AbortSignal.timeout(TIMEOUT),
  });
  return await resp.json();
}

async function ghJson(path: string) {
  const headers: Record<string, string> = { Accept: "application/vnd.github+json" };
  const tok = env("GH_TOKEN");
  if (tok) headers["Authorization"] = "Bearer " + tok;
  return await getJson(GH_API + path, headers);
}

async function coprJson(path: string) {
  return await getJson(COPR_API + path);
}

async function tgCall(method: string, params: Record<string, string>) {
  const token = env("TG_BOT_TOKEN");
  if (!token) return null;
  try {
    const resp = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params),
      signal: AbortSignal.timeout(TIMEOUT),
    });
    return await resp.json();
  } catch (_e) {
    return null;
  }
}

const MENU = JSON.stringify({
  keyboard: [
    [{ text: "📊 Статус" }, { text: "📈 Прогресс" }],
    [{ text: "❌ Ошибки" }, { text: "📦 Сборки" }],
  ],
  resize_keyboard: true,
});

const HELLO = [
  "candy-rpm на связи (Supabase Edge Function, без расписания).",
  "📊 Статус — последние прогоны update.yml",
  "📈 Прогресс — джобы текущего прогона",
  "❌ Ошибки — упавшие джобы и сборки",
  "📦 Сборки — последние сборки в COPR",
  "/run — запустить план-прогон update.yml (только владелец)",
].join("\n");

function mark(conclusion: string | null, status: string): string {
  if (status !== "completed") return "⏳";
  const m: Record<string, string> = {
    success: "✅",
    failure: "❌",
    cancelled: "⚪",
    skipped: "⏭",
  };
  return m[conclusion ?? ""] ?? "❓";
}

async function actionStatus(): Promise<string> {
  const data = await ghJson(
    `/repos/${repo()}/actions/workflows/update.yml/runs?per_page=5`,
  );
  const runs = data?.workflow_runs ?? [];
  if (runs.length === 0) return "Прогонов update.yml ещё не было.";
  const out = [`Последние прогоны update.yml (${repo()}):`];
  for (const r of runs) {
    out.push(
      `${mark(r.conclusion, r.status ?? "")} #${r.run_number} ${r.event} ` +
        `${String(r.created_at ?? "").slice(0, 16).replace("T", " ")} ` +
        `${r.conclusion ?? r.status}`,
    );
  }
  return out.join("\n");
}

async function actionProgress(): Promise<string> {
  const data = await ghJson(
    `/repos/${repo()}/actions/workflows/update.yml/runs?per_page=1`,
  );
  const runs = data?.workflow_runs ?? [];
  if (runs.length === 0) return "Прогонов update.yml ещё не было.";
  const run = runs[0];
  const jobs = await ghJson(`/repos/${repo()}/actions/runs/${run.id}/jobs?per_page=100`);
  const out = [`Прогон #${run.run_number} — ${run.status}`];
  for (const j of jobs?.jobs ?? []) {
    out.push(`${mark(j.conclusion, j.status ?? "")} ${j.name}`);
  }
  return out.join("\n");
}

async function actionErrors(): Promise<string> {
  const data = await ghJson(
    `/repos/${repo()}/actions/workflows/update.yml/runs?per_page=1`,
  );
  const runs = data?.workflow_runs ?? [];
  const lines: string[] = [];
  if (runs.length > 0) {
    const jobs = await ghJson(
      `/repos/${repo()}/actions/runs/${runs[0].id}/jobs?per_page=100`,
    );
    for (const j of jobs?.jobs ?? []) {
      if (j.conclusion === "failure") lines.push(`❌ джоба: ${j.name}`);
    }
  }
  const builds = await coprJson(
    `/build/list/?ownername=${env("COPR_OWNER", "arcticlore")}` +
      `&projectname=${env("COPR_PROJECT", "candy")}&limit=40`,
  );
  const items = Array.isArray(builds) ? builds : (builds?.items ?? []);
  for (const b of items.slice(0, 40)) {
    if (b.state === "failed") {
      lines.push(`❌ сборка ${b.id}: ${b.source_package?.name}`);
    }
  }
  return lines.length > 0 ? lines.slice(0, 40).join("\n") : "Ошибок нет.";
}

async function actionBuilds(): Promise<string> {
  const builds = await coprJson(
    `/build/list/?ownername=${env("COPR_OWNER", "arcticlore")}` +
      `&projectname=${env("COPR_PROJECT", "candy")}&limit=10`,
  );
  const items = Array.isArray(builds) ? builds : (builds?.items ?? []);
  if (items.length === 0) return "COPR не отдал сборки.";
  const icons: Record<string, string> = {
    succeeded: "✅",
    failed: "❌",
    running: "⏳",
    pending: "🕒",
  };
  const out = ["Последние сборки COPR:"];
  for (const b of items.slice(0, 10)) {
    const src = b.source_package ?? {};
    out.push(
      `${icons[b.state] ?? "•"} ${b.id} ${src.name} ${src.version ?? ""} ${b.state}`,
    );
  }
  return out.join("\n");
}

/** workflow_dispatch update.yml в режиме плана. Только владелец. */
async function actionRun(chatId: string): Promise<string> {
  if (!isOwner(chatId)) return "Эта команда доступна только владельцу.";
  const tok = env("GH_TOKEN");
  if (!tok) return "GH_TOKEN не задан — запуск невозможен.";
  try {
    const resp = await fetch(
      `${GH_API}/repos/${repo()}/actions/workflows/update.yml/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: "Bearer " + tok,
          Accept: "application/vnd.github+json",
          "User-Agent": "candy-rpm-tg-webhook",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "master", inputs: { plan_only: "true" } }),
        signal: AbortSignal.timeout(TIMEOUT),
      },
    );
    if (resp.status === 201 || resp.status === 204) {
      return "Запустил план-прогон update.yml.";
    }
    return `GitHub отказал: ${resp.status}.`;
  } catch (_e) {
    return "GitHub недоступен.";
  }
}

/** Текст сообщения → текст ответа. */
async function route(text: string, chatId = ""): Promise<string> {
  const t = (text ?? "").trim();
  const low = t.toLowerCase().replace(/^\/+/, "");
  if (!t) return HELLO;
  if (low.startsWith("start") || low.startsWith("help")) return HELLO;
  if (low.includes("статус") || low.startsWith("status")) return await actionStatus();
  if (low.includes("прогресс") || low.startsWith("progress")) return await actionProgress();
  if (low.includes("ошиб") || low.startsWith("error") || low.startsWith("fail")) {
    return await actionErrors();
  }
  if (low.includes("сборк") || low.startsWith("build")) return await actionBuilds();
  if (low.startsWith("run")) return await actionRun(chatId);
  return "Не понял. Нажми кнопку меню или /help.";
}

/** Вебхук обязан предъявить секрет: иначе любой может слать апдейты. */
function secretOk(req: Request): boolean {
  const want = env("TG_SECRET");
  if (!want) return false;
  const got = req.headers.get("X-Telegram-Bot-Api-Secret-Token");
  return !!got && got === want;
}

async function handleUpdate(update: Record<string, any>): Promise<void> {
  let msg = update.message ?? update.edited_message ?? null;
  let text = "";
  if (msg) {
    text = msg.text ?? "";
  } else {
    const cb = update.callback_query ?? {};
    msg = cb.message ?? null;
    text = cb.data ?? "";
  }
  const chat = msg?.chat?.id;
  if (chat === undefined || chat === null) return;
  // Чужим чатам бот не отвечает вовсе: состояние CI — не публичные данные.
  if (ownerChats().size > 0 && !isOwner(chat)) return;
  const reply = (await route(text, String(chat))).slice(0, LIMIT);
  await tgCall("sendMessage", {
    chat_id: String(chat),
    text: reply,
    reply_markup: MENU,
    disable_web_page_preview: "true",
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === "GET") {
    // GET держит проект живым: free-tier засыпает от безделья,
    // поэтому monitor.yml пингует этот адрес по расписанию.
    return new Response("candy-rpm telegram webhook alive\n", { status: 200 });
  }
  if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
  if (!secretOk(req)) return new Response("bad secret", { status: 401 });
  let update: Record<string, any>;
  try {
    update = await req.json();
  } catch (_e) {
    return new Response("ignored", { status: 200 }); // 200, иначе Telegram ретраит вечно
  }
  try {
    await handleUpdate(update);
  } catch (e) {
    console.error("handler error:", e);
  }
  return new Response("ok", { status: 200 });
});
