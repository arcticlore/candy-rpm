#!/usr/bin/env bash
# check-deps.sh SRPM... — дозор BuildRequires.
# Сухой прогон `dnf builddep --assumeno` с работающим интернетом: если dnf
# не может разрешить зависимости (no match for argument / Problem: /
# nothing provides) — SRPM блокируется (перемещается в SRPMS/blocked/),
# чтобы не ушёл в COPR и не кормил билдеров ошибками. Лог — logs/deps.log.
#
# ВАЖНО: dnf5 с --assumeno выходит с RC=1 и при успешном разрешении
# («Операция прервана пользователем») — поэтому ориентируемся ТОЛЬКО на
# текст жалоб в выводе, а не на код возврата.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs SRPMS/blocked

# жалобы = dnf не нашёл/не может поставить требуемое
WOES="no match for argument|problem:|nothing provides|unable to find a match|\
cannot be installed|could not resolve|not found in the repository|\
не найдено совпадени|ничего не предоставляет|невозможно установить|не удалось разрешить"
# инфра-сбои (не «битые зависимости»): SSL/сертификаты — ретраим, а не блокируем
SSLWOE="ssl.*cert|ssl error|ssl handshake|ssl connect|ssl connection|ssl problem|certificat|сертифик|истек|unable to get local issuer|not authenticat|has expired|verification failed|проверк"

PROB=0
for SRPM in "$@"; do
    [ -f "$SRPM" ] || continue
    NAME="$(rpm -qp --qf '%{NAME}' "$SRPM" 2>/dev/null)" || NAME="${SRPM##*/}"

    OUT=""
    SSL_FAIL=0
    for attempt in 1 2 3; do
        OUT="$(dnf builddep --assumeno -y "$SRPM" 2>&1)"
        if echo "$OUT" | grep -qiE "$SSLWOE"; then
            SSL_FAIL=$attempt
            echo "[RETRY] $NAME: dnf c SSL ($attempt/3), жду 15 c" | tee -a logs/deps.log
            sleep 15
            continue
        fi
        SSL_FAIL=0
        break
    done
    if [ "$SSL_FAIL" -gt 0 ]; then
        {
            echo "[WARN] $NAME: dnf трижды упёрся в SSL-ошибку — не блокирую (это инфра, не «битые зависимости»):"
            echo "$OUT" | grep -iE "$SSLWOE" | head -4 | sed 's/^/    /'
        } | tee -a logs/deps.log
        continue
    fi

    if ! echo "$OUT" | grep -qiE "$WOES"; then
        echo "[OK-dep] $NAME" | tee -a logs/deps.log
        continue
    fi

    PROB=$((PROB + 1))
    echo "[BLOCK] $NAME — dnf не может разрешить BuildRequires:" | tee -a logs/deps.log
    echo "$OUT" | grep -iE "$WOES" | head -6 | sed 's/^/    /' | tee -a logs/deps.log
    mv "$SRPM" SRPMS/blocked/ 2>/dev/null || true
done

[ "$PROB" -eq 0 ]