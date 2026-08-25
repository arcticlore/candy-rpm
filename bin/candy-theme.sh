#!/usr/bin/env bash
# candy-theme.sh — ставит сладкую тему: starship + fastfetch + alias
set -e
R="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p ~/.config/{starship,fastfetch} ~/.local/bin
cp "$R/dotfiles/candy-starship.toml" ~/.config/starship.toml
cp "$R/dotfiles/candy-fastfetch.jsonc" ~/.config/fastfetch.jsonc
grep -q "starship init" ~/.bashrc || echo 'eval "$(starship init bash)"' >> ~/.bashrc
alias fastfetch >/dev/null 2>&1 || echo "alias ff=fastfetch" >> ~/.bashrc
echo "🍬 тема установлена: starship (конфетный промпт) + fastfetch (конфиг)"
echo "   открой новый терминал или: source ~/.bashrc && fastfetch"
