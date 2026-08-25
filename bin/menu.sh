#!/usr/bin/env bash
# candy-menu — меню при открытии терминала.
# Свои пункты добавляй в файл ~/.config/candy-menu.conf (формат: Название|команда)
CONF="${CANDY_MENU:-$HOME/.config/candy-menu.conf}"

if [ ! -f "$CONF" ]; then
    mkdir -p "$(dirname "$CONF")"
    cat > "$CONF" <<'EOF'
# Формат: Название|команда  (добавляй свои строки ниже)
Дашборд (live)|~/terminal-eye-candy-rpm/bin/dashboard.sh -w 30
Дашборд (один кадр)|~/terminal-eye-candy-rpm/bin/dashboard.sh
opencode|opencode
Статус конвейера|~/terminal-eye-candy-rpm/bin/status.sh
Утренний отчёт|less -R ~/terminal-eye-candy-rpm/logs/morning-report.md
Перезапустить няню|systemctl --user restart candy-babysit && sleep 2 && systemctl --user is-active candy-babysit
Bash|bash
EOF
fi

entries() { grep -vE '^\s*(#|$)' "$CONF"; }
count()   { entries | wc -l; }

while true; do
    clear
    echo "╔═════════════ CANDY MENU ═════════════╗"
    local_i=0
    while IFS='|' read -r lbl cmd; do
        ((local_i++)); echo "  $local_i) $lbl"
    done < <(entries)
    echo "  a) ➕ добавить программу"
    echo "  d) ➖ удалить программу"
    echo "  q) выход"
    echo "╚══════════════════════════════════════╝"
    read -rp "выбери номер: " choice
    case "$choice" in
    q|Q|"") clear; break ;;
    a|A)
        read -rp "Название программы: " lbl
        [ -z "$lbl" ] && continue
        read -rp "Команда запуска: " cmd
        [ -z "$cmd" ] && continue
        echo "$lbl|$cmd" >> "$CONF"
        echo "✅ добавлено"; sleep 1 ;;
    d|D)
        n=0
        while IFS='|' read -r lbl cmd; do ((n++)); echo "  $n) $lbl"; done < <(entries)
        read -rp "номер для удаления: " dn
        [[ "$dn" =~ ^[0-9]+$ ]] || continue
        awk -v n="$dn" 'NR!=n' "$CONF" > "$CONF.tmp" && mv "$CONF.tmp" "$CONF"
        echo "🗑 удалено"; sleep 1 ;;
    esac
    n=0; hit=""
    while IFS='|' read -r lbl cmd; do
        ((n++))
        if [ "$n" = "$choice" ]; then hit="$cmd"; break; fi
    done < <(entries)
    if [ -n "$hit" ]; then
        clear; bash -c "$hit"; echo; read -rp "↩ Enter — в меню..."
    fi
done
