# Телеграм-бот как вебхук (Supabase Edge Function)

Боевой хост бота. Long-poll в `.github/workflows/telegram.yml` оставлен только
как путь отката и по расписанию больше не запускается.

| что | значение |
| --- | --- |
| проект | `candy-bot`, ref `eikrdvuoihrpgegkcjlk`, регион `eu-central-1`, план free |
| функция | slug `tg`, `verify_jwt: false` (Telegram не умеет слать JWT) |
| адрес | `https://eikrdvuoihrpgegkcjlk.supabase.co/functions/v1/tg` |
| исходник | `supabase/functions/tg/index.ts` — построчный порт `vercel/api/telegram.py` |

## Секреты (Project Settings → Edge Functions → Secrets)

| имя | смысл |
| --- | --- |
| `TG_BOT_TOKEN` | токен бота |
| `TG_SECRET` | секрет вебхука, он же заголовок `X-Telegram-Bot-Api-Secret-Token` |
| `TG_OWNER_CHAT` | chat_id владельцев через запятую — бот отвечает только им |
| `GH_REPO` | `arcticlore/candy-rpm` |
| `GH_TOKEN` | PAT с `actions:write` — нужен только для `/run` |
| `COPR_OWNER` / `COPR_PROJECT` | `arcticlore` / `candy` |

Пустой `TG_SECRET` означает «отвергать всё»: без него функция не примет ни один
POST. Пустой `TG_OWNER_CHAT` означает «владельцев нет»: `/run` не сработает ни у
кого.

## Привязка вебхука

```sh
curl -sS "https://api.telegram.org/bot$TG_BOT_TOKEN/setWebhook" \
  -d url=https://eikrdvuoihrpgegkcjlk.supabase.co/functions/v1/tg \
  -d secret_token="$TG_SECRET" \
  -d drop_pending_updates=true \
  -d 'allowed_updates=["message","edited_message","callback_query"]'
curl -sS "https://api.telegram.org/bot$TG_BOT_TOKEN/getWebhookInfo"
```

`getWebhookInfo` — главный монитор: `pending_update_count` и
`last_error_message` показывают, доходят ли апдейты и что именно сломалось.

## Откат на long-poll

```sh
curl -sS "https://api.telegram.org/bot$TG_BOT_TOKEN/deleteWebhook"
```

затем включить обратно workflow `telegram bot` (он сам проверяет через
`getWebhookInfo`, что вебхук снят, и отказывается стартовать иначе) и вернуть
ему расписание. Одновременно два хоста жить не могут: Telegram отдаёт
`409 Conflict`.

## Почему не Vercel

Код для Vercel лежит рядом (`vercel/api/telegram.py`) и остаётся рабочим, но
деплой туда требует Login Connection к GitHub у аккаунта Vercel — без неё API
отказывается и линковать репозиторий, и принимать первый деплой проекта.
Как только связь появится, можно импортировать репозиторий с Root Directory
`vercel`, перенести те же переменные и переставить `setWebhook` на адрес
Vercel: поведение функции идентично, расходятся только рантайм и хостинг.

## Пробуждение

Free-tier Supabase усыпляет проект от безделья, поэтому `monitor.yml`
(каждые 2 часа) дёргает `GET` этого же адреса: функция отвечает
`candy-rpm telegram webhook alive`, проект считается активным, бот не засыпает.
