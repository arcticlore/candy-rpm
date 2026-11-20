# Telegram-бот на Vercel (вебхук, 24/7)

`tools/tg-notify.py --listen` — long-poll: он жив ровно столько, сколько длится
джоба `telegram.yml`, и работает ТОЛЬКО когда GitHub соизволит запустить cron.
Здесь другая модель: Telegram сам вызывает HTTP-функцию на каждое сообщение.
Никакого расписания, «окон простоя» нет по построению.

Цена: у функции нет ни репозитория, ни shell'а. Поэтому ответы собираются из
GitHub Actions API, COPR API и веток `state/*`, а всё, что требует сборки,
запускается через `workflow_dispatch` — функция отвечает сразу, работу делает
GitHub.

## Что внутри

| Файл | Назначение |
|---|---|
| `api/telegram.py` | сама функция: проверка секрета, маршрутизация, ответы |
| `vercel.json` | `maxDuration 30`, корень `/` отвечает тем же обработчиком |

## Развёртывание

1. Создать проект на Vercel из репозитория, **Root Directory = `vercel`**,
   framework preset — `Other`.
2. Environment Variables (Production):

   | Переменная | Значение |
   |---|---|
   | `TG_BOT_TOKEN` | токен бота (тот же, что в секрете GitHub) |
   | `TG_SECRET` | любая длинная случайная строка |
   | `TG_OWNER_CHAT` | chat_id владельцев через запятую (`7502676910,5174354533`): бот отвечает только им и только им даёт `/run` |
   | `GH_REPO` | `arcticlore/candy-rpm` |
   | `GH_TOKEN` | fine-grained PAT с `actions: write` — только если нужен `/run` |
   | `COPR_OWNER` / `COPR_PROJECT` | `arcticlore` / `candy` |

3. Деплой, затем один раз привязать вебхук:

   ```sh
   curl -s "https://api.telegram.org/bot$TG_BOT_TOKEN/setWebhook" \
     -d "url=https://<project>.vercel.app/api/telegram" \
     -d "secret_token=$TG_SECRET" \
     -d "drop_pending_updates=true" \
     -d 'allowed_updates=["message","callback_query"]'
   ```

4. Проверить: `curl "https://api.telegram.org/bot$TG_BOT_TOKEN/getWebhookInfo"` —
   `pending_update_count` должен быть 0, `last_error_message` пустым.

## Обязательный шаг на стороне GitHub

Long-poll и вебхук **несовместимы**: пока жив `getUpdates`, Telegram отдаёт
ошибку 409 на вебхук и наоборот. После включения вебхука выключите
`.github/workflows/telegram.yml` (удалить `schedule` или отключить workflow).
`monitor.yml` и `bin/converge.sh` при этом продолжают слать уведомления
обычным `sendMessage` — их трогать не нужно.

Откат: `deleteWebhook`, вернуть cron в `telegram.yml`.

## Чего функция принципиально не может

* выполнять `./bin/status.sh`, `./bin/dashboard.sh` и читать `logs/update.log`
  — этих файлов нет в рантайме Vercel (да и в чекауте GitHub Actions они
  пустые: каждый прогон начинается с чистой копии репозитория);
* держать состояние между вызовами — язык/настройки надо хранить снаружи
  (ветка `state/*` через contents API или Vercel KV);
* выполнять долгие задачи: лимит функции здесь 30 с, Hobby-план допускает
  максимум 60 с. Всё длинное — только `workflow_dispatch`.
