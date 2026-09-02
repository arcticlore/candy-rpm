# 📦 Пакеты репозитория arcticlore/candy

Установка: `sudo dnf install dnf-plugins-core && sudo dnf copr enable arcticlore/candy`

## Каталог

| Пакет | Описание | Запуск | Источник |
|---|---|---|---|
| **bandwhich** | Какой процесс жрёт сеть — в реальном времени | `sudo bandwhich -i wlan0` | github.com/imsnif/bandwhich |
| **bottom** | Cross-platform graphical process/system monitor | `btm — монитор процессов с графиками` | github.com/ClementTsang/bottom |
| **broot** | Дерево каталогов с навигацией и предпросмотром | `broot — интерактивное дерево файлов` | github.com/Canop/broot |
| **csview** | Быстрый csv-просмотрщик с поддержкой CJK/эмодзи | `—` | github.com/wfxr/csview |
| **curlie** | The power of curl, the ease of use of httpie | `curlie https://api.github.com` | github.com/rs/curlie |
| **doggo** | Fast command-line DNS client for humans | `doggo example.com MX` | github.com/mr-karan/doggo |
| **fx** | Terminal JSON viewer and processor | `cat data.json | fx — интерактивный JSON` | github.com/antonmedv/fx |
| **glow** | Рендер markdown прямо в терминале с подсветкой (charm) | `glow README.md — читай markdown в терминале` | github.com/charmbracelet/glow |
| **gping** | Ping, but with a graph | `gping 1.1.1.1 — ping с графиком` | github.com/orf/gping |
| **gum** | Glamorous tool для шелл-скриптов: спиннеры, выбор, ввод (charm-стиль) | `gum choose 'вариант 1' 'вариант 2'; gum spin -- sleep 2` | github.com/charmbracelet/gum |
| **hyperfine** | Бенчмарк команд со статистикой и экспортом | `hyperfine 'sleep 0.3'` | github.com/sharkdp/hyperfine |
| **just** | Современный command runner (Make без боли) | `just <рецепт>; just --list` | github.com/casey/just |
| **lazydocker** | Lazier way to manage everything docker | `запусти lazydocker при работающем docker` | github.com/jesseduffield/lazydocker |
| **lazygit** | Simple terminal UI for git commands | `запусти lazygit внутри git-репозитория` | github.com/jesseduffield/lazygit |
| **lf** | Terminal file manager | `lf — файловый менеджер` | github.com/gokcehan/lf |
| **mise** | Менеджер рантаймов node/python/ruby — быстрый asdf-killer | `mise use --pin node@22` | github.com/jdx/mise |
| **oha** | HTTP бенчмарк с красивым TUI | `oha -n 200 https://example.com` | github.com/hatoo/oha |
| **scc** | Счётчик строк кода по языкам — быстрее cloc | `scc ./project` | github.com/boyter/scc |
| **sd** | Intuitive find & replace CLI (sed alternative) | `sd 'старый текст' 'новый текст' file.txt` | github.com/chmln/sd |
| **starship** | Minimal, blazing-fast, infinitely customizable cross-shell prompt | `eval "$(starship init bash)" — добавь в ~/.bashrc` | github.com/starship/starship |
| **tealdeer** | Быстрый tldr-client: примеры команд вместо man | `tldr tar — шпаргалки` | github.com/dbrgn/tealdeer |
| **tokei** | Статистика кода по языкам, молниеносная | `tokei ./src` | github.com/XAMPPRocky/tokei |
| **trippy** | Гибрид mtr/traceroute с живым TUI | `sudo trip example.com` | github.com/fujiapple852/trippy |
| **viddy** | Modern watch command (with key bindings and diffs) | `viddy 'df -h' — watch с подсветкой diff` | github.com/sachaos/viddy |
| **watchexec** | Перезапуск команд при изменении файлов | `watchexec -- make test` | github.com/watchexec/watchexec |
| **xh** | Friendly and fast tool for sending HTTP requests | `xh GET https://api.github.com` | github.com/ducaale/xh |
| **yazi** | Blazing fast terminal file manager written in Rust | `yazi — файловый менеджер; выход Q` | github.com/sxyazi/yazi |
| **albafetch** | Faster neofetch alternative written in C | `albafetch` | github.com/alba4k/albafetch |
| **animfetch** | Animated system fetch pinned above your shell | `animfetch — анимированный fetch` | github.com/Andrew-Velox/animfetch |
| **archey4** | Arch Linux system information tool (maintained fork) | `archey` | github.com/HorlogeSkynet/archey4 |
| **bacon** | Фоновый компилятор/тестер Rust-проектов на лету | `bacon — фоновая проверка проекта` | github.com/Canop/bacon |
| **bunnyfetch** | Tiny system info fetch utility | `bunnyfetch` | github.com/Rosettea/bunnyfetch |
| **CrabFetch** | Extremely fast and featureful command-line fetcher | `crabfetch` | github.com/LivacoNew/CrabFetch |
| **ctop** | top для контейнеров (docker/podman) | `ctop — живой монитор контейнеров` | github.com/bcicen/ctop |
| **disfetch** | Yet another *nix distro fetching program, less complex | `disfetch` | github.com/q60/disfetch |
| **dua** | Анализ места на диске + интерактивное удаление | `dua i — интерактивный режим` | github.com/Byron/dua-cli |
| **dysk** | df для людей: диски человекочитаемо | `dysk — все точки монтирования` | github.com/Canop/dysk |
| **ghfetch** | Neofetch-like utility to fetch GitHub info in the terminal | `ghfetch <логин-github>` | github.com/SafarSoFar/ghfetch |
| **gitfetch** | GitHub contribution visualization tool inspired by neofetch | `gitfetch <логин-github>` | github.com/FabricSoul/gitfetch |
| **grex** | Генератор регулярок из примеров строк | `grex a1 b2 → '^a[12]b[12]$'` | github.com/pemistahl/grex |
| **kondo** | Чистка build-артефактов проектов (node_modules/target) | `kondo ~/dev — найти мусор` | github.com/tbillington/kondo |
| **macchina** | System information fetcher with an emphasis on performance | `macchina — инфа о системе` | github.com/Macchina-CLI/macchina |
| **nb** | Заметки/закладки/блокноты — всё в CLI (один bash-файл) | `nb add текст заметки; nb ls` | github.com/xwmx/nb |
| **neofetch** | Command-line system information tool | `neofetch` | github.com/dylanaraps/neofetch |
| **nerdfetch** | POSIX nix fetch script using Nerdfonts | `nerdfetch (нужен Nerd Font)` | codeberg.org/thatonecalculator/NerdFetch |
| **pet** | Менеджер сниппетов: сохрани и вставь команду | `pet new / pet exec <имя>` | github.com/knqyf263/pet |
| **pokemon-icat** | Show any Pokemon sprite in your terminal | `pokemon-icat pikachu — спрайт покемона` | github.com/aflaag/pokemon-icat |
| **presenterm** | Терминальные презентации из markdown с темами | `presenterm slides.md` | github.com/mfontanini/presenterm |
| **pridefetch** | Neofetch, but gay | `pridefetch` | github.com/cartoon-raccoon/pridefetch |
| **rxfetch** | Custom system fetching tool written in bash | `rxfetch` | github.com/mngshm/rxfetch |
| **slides** | Презентации прямо в терминале из markdown | `slides deck.md — презентация` | github.com/maaslalani/slides |
| **ufetch** | Tiny system info for Unix-like operating systems | `ufetch` | gitlab.com/jschx/ufetch |
| **wtfutil** | Личный дашборд-терминал из модулей (ops-style) | `wtfutil — дашборд модулей` | github.com/wtfutil/wtfutil |
| **zk** | Zettelkasten-заметки в терминале | `zk new; zk list` | github.com/zk-org/zk |
| **arttime** | ASCII art, clock, timer and time manager for the terminal | `arttime — ASCII-арт+часы; arttime -m сообщение` | github.com/poetaman/arttime |
| **ascii-image-converter** | Конвертация изображений в ASCII-art прямо в терминале | `ascii-image-converter photo.jpg --color` | github.com/TheZoraiz/ascii-image-converter |
| **ascii-rain** | Comfy rain for your console | `ascii-rain — дождь, Ctrl+C выход` | github.com/nkleemann/ascii-rain |
| **ascsaver** | Collection of ASCII screensavers (dogs/globe/nasa/star_wars) | `—` | gitlab.com/mezantrop/ascsaver |
| **cbeams** | Colorful animated beams in the terminal | `cbeams — цветные лучи` | github.com/tartley/cbeams |
| **cli-fx** | Terminal visual effects library in pure bash (glitch/plasma/rain) | `source /usr/share/cli-fx/lib/core.sh — эффекты в своих скриптах` | github.com/lukeslp/cli-fx |
| **ctree** | A Christmas tree right from your terminal | `ctree — новогодняя ёлка` | github.com/gleich/ctree |
| **cyme** | lsusb с красивым выводом и фильтрами | `cyme` | github.com/tuna-f1sh/cyme |
| **duckpond** | Ducks swimming in a pond, in your terminal | `duckpond.sh — утки на пруду` | github.com/gsobell/duckpond.sh |
| **fend** | Калькулятор произвольной точности | `echo '1+2' | fend` | github.com/printf/fend |
| **genact** | Генератор безумной активности — притворись хакером | `genact — Ctrl+C остановить` | github.com/svenstaro/genact |
| **gh-screensaver** | Screensaver extension for gh (fireworks/starfield/pipes) | `gh screensaver -e fireworks (нужен GitHub CLI)` | github.com/vilmibm/gh-screensaver |
| **joshuto** | ranger-подобный файловый менеджер (Rust) | `—` | github.com/kamiyaa/joshuto |
| **lavat** | Lava lamp in the terminal | `lavat — лава-лампа; клавиши +/- меняют скорость` | github.com/AngelJumbo/lavat |
| **lolcrab** | lolcat с шумом и радугой (Rust) | `—` | github.com/mazznoer/lolcrab |
| **maze** | Animated maze generator screensaver | `maze.py — генерация лабиринта` | github.com/pipeseroni/maze.py |
| **pipes.rs** | Over-engineered pipes.sh на Rust | `—` | github.com/lhvy/pipes-rs |
| **pipes.sh** | Animated pipes terminal screensaver | `pipes.sh — трубы-скринсейвер, Esc для выхода` | github.com/pipeseroni/pipes.sh |
| **pipesX** | Animated pipes screensaver, extended edition | `pipesX.sh` | github.com/pipeseroni/pipesX.sh |
| **PyBonsai** | Procedural ASCII bonsai tree generator | `pybonsai — растит бонсай` | pypi.org/project/pybonsai |
| **snakes** | Snakes crawling across your terminal | `snakes.pl — змейки` | github.com/pipeseroni/snakes.pl |
| **snowmachine** | Snow in your terminal | `snowmachine — снегопад` | pypi.org/project/snowmachine |
| **tabiew** | TUI-просмотр csv/parquet/json датасетов | `tabiew data.csv` | github.com/fathulfahmy/tabiew |
| **terminal-parrot** | Party parrot time, in your terminal | `terminal-parrot — танцующий попугай` | github.com/jmhobbs/terminal-parrot |
| **terminaltexteffects** | Terminal text effects engine — анимации печати и эффектов в терминале | `tte "твой текст" — эффекты печати; tte --list-effects` | pypi.org/project/terminaltexteffects |
| **termshot** | Скриншот команды в виде терминального окна | `termshot --out shot.png -- ls -la` | github.com/homeport/termshot |
| **tfire** | Fire animation in your terminal | `tfire.sh — огонь` | github.com/tech-chad/tfire |
| **tspace** | Fly a little spaceship around your terminal | `tspace.sh — кораблик` | github.com/mtklr/tspace |
| **tty-clock** | Digital clock in ncurses | `tty-clock -c -C 4 — часы по центру, цвет 4` | github.com/xorg62/tty-clock |
| **ttyper** | Тренажёр слепой печати в терминале | `ttyper — тест слепой печати (ru: --language ru1000)` | github.com/max-niederman/ttyper |
| **ttysvr** | Набор скринсейверов для терминала | `—` | github.com/cxreiff/ttysvr |
| **typioca** | Минималистичный тест скорости печати | `typioca — печать на скорость` | github.com/bloznelis/typioca |
| **unimatrix** | Матрица из unicode-символов (гибкий аналог cmatrix) | `unimatrix -s 96 — unicode-матрица` | github.com/will8211/unimatrix |
| **weave** | Weaving pattern screensaver | `weave.sh — плетение узоров` | github.com/pipeseroni/weave.sh |
| **zenta** | Meditative zen terminal screensaver | `zenta.sh — дзен-скринсейвер` | github.com/e6a5/zenta |
| **artem** | Convert images from multiple formats to ASCII art | `artem photo.jpg — картинка в ASCII` | github.com/FineFindus/artem |
| **cadubi** | Creative ASCII drawing utility | `cadubi — рисование ASCII` | github.com/statico/cadubi |
| **diagram** | ASCII-диаграммы из текста | `diagram --svg out.svg in.txt` | github.com/esimov/diagram |
| **dog** | DNS-клиент doggo-класса с цветным выводом | `—` | github.com/ogham/dog |
| **durdraw** | ANSI/ASCII and Unicode art editor with animation | `durdraw — редактор ANSI-арта` | github.com/cmang/durdraw |
| **jp2a** | Convert JPG/PNG images to ASCII art | `jp2a photo.jpg --width=80` | github.com/Talinx/jp2a |
| **parrotsay** | Party parrot says things in your terminal | `parrotsay 'Привет!'` | npmjs.com/package/parrotsay |
| **ponysay** | cowsay reimplemention for ponies, 256-color | `ponysay 'Привет!' или ponysay -l список пони` | github.com/erkin/ponysay |
| **pscircle** | Visualize processes as a circular tree wallpaper | `pscircle --output=pscircle.png — процессы кругом` | gitlab.com/mildlyparallel/pscircle |
| **ricksay** | Rick and Morty quotes of the day (cowsay clone) | `ricksay — цитата Рика и Морти` | github.com/kochie/ricksay |
| **tetris** | Тетрис в терминале | `tetris — стрелки и пробел` | github.com/samtay/tetris |
| **tulizu** | Tool to customize ASCII art in /etc/issue | `tulizu --help — арт для /etc/issue` | github.com/loh-tar/tulizu |
| **viu** | View images right from the terminal | `viu photo.jpg — картинка прямо в терминале` | github.com/atanunq/viu |
| **yosay** | Tell Yeoman what to say, ANSI-art speech bubbles | `yosay 'Привет!'` | github.com/yeoman/yosay |
| **choose** | Умный cut на Rust | `—` | github.com/theryangeary/choose |
| **erdtree** | Анализ дерева каталогов с размерами | `ert — размеры по папкам` | github.com/solidiquis/erdtree |
| **flavours** | Manager and builder for Base16 base00-FF schemes | `flavours apply gruvbox-dark` | github.com/Misterio77/flavours |
| **linuxwave** | Generate music from the entropy of Linux | `linuxwave -o out.wav — музыка из энтропии` | github.com/orhun/linuxwave |
| **oh-my-zsh** | Framework for managing zsh configuration with 300+ plugins | `экспортируй ZSH=/usr/share/oh-my-zsh и source oh-my-zsh.sh в ~/.zshrc` | github.com/ohmyzsh/ohmyzsh |
| **powerlevel10k** | Zsh theme focused on speed, flexibility and out-of-box UX | `echo 'source /usr/share/powerlevel10k/powerlevel10k.zsh-theme' >> ~/.zshrc` | github.com/romkatv/powerlevel10k |
| **pure** | Pretty, minimal and fast ZSH prompt | `npm-глобал: добавь 'prompt pure' через antigen/zplug` | github.com/sindresorhus/pure |
| **pywal** | Generate and change color-schemes on the fly | `wal -i обои.jpg — палитра из картинки` | pypi.org/project/pywal |
| **tint** | Terminal theme switcher with live preview | `tint dracula — сменить тему терминала; tint -l список` | github.com/corygabrielsen/tint |
| **wallust** | Generate colorschemes from images (pywal successor) | `wallust run обои.jpg` | codeberg.org/explosion-mental/wallust |
| **himalaya** | Email-клиент целиком в CLI | `himalaya list — письма в терминале` | github.com/pimalaya/himalaya |
| **rickrollrc** | Rick Astley rickrolls your terminal | `—` | github.com/keroserene/rickrollrc |
| **video-to-ascii** | Играть видео прямо в терминале ASCII-символами | `video-to-ascii -f clip.mp4 — нужны ffmpeg и portaudio` | pypi.org/project/video-to-ascii |
| **ascii-patrol** | ASCII Patrol — аркада в стиле Moon Patrol | `aptr` | github.com/msokalski/ascii-patrol |
| **gittype** | Тренажёр печати на коде твоих репозиториев | `gittype в каталоге репо` | github.com/unhappychoice/gittype |
| **rmpc** | Красивый TUI клиент MPD | `rmpc — нужен запущенный mpd` | github.com/mierak/rmpc |
| **systeroid** | sysctl(8) с TUI-графикой | `systeroid --tui` | github.com/orhun/systeroid |
| **termusic** | TUI музыкальный плеер (mpv/ytdlp) | `—` | github.com/tramhao/termusic |
| **zenith** | Системный дашборд: CPU/GPU/сеть/диски графиками | `zenith` | github.com/bvaisnard/zenith |
| **colorls** | Prettifies ls output with colors and font-awesome icons | `colorls — красивый ls (нужен Nerd Font)` | github.com/athityakumar/colorls |
| **musikcube** | Terminal-based music player, library and streaming server | `musikcube — консольный плеер` | github.com/clangen/musikcube |
| **peaclock** | Часы/секундомер/таймер с цветными цифрами | `peaclock` | github.com/octobanana/peaclock |
| **pokete** | Покемоны в терминале (полноценная игра) | `pokete.py` | github.com/lxgr-linux/pokete |
| **zellij** | Terminal workspace with panels, plugins and layouts | `zellij — мультиплексор, Ctrl+p для помощи` | github.com/zellij-org/zellij |
| **diagon** | Interactive ASCII diagram generator (math/tree/table/flow) | `diagon math — интерактивные ASCII-диаграммы` | github.com/ArthurSonzogni/Diagon |
| **hollywood** | Fill your console with Hollywood melodrama technobabble | `hollywood — консоль хакера из кино (нужен byobu)` | github.com/dustinkirkland/hollywood |
| **Rio** | Hardware-accelerated terminal emulator focused on typography | `—` | github.com/raphamorim/rio |

## Отключённые (по причинам)

- ~~catnap~~ — Компилятор nim отсутствует в Fedora 44; включить после установки choosenim
- ~~nitch~~ — Компилятор nim отсутствует в Fedora 44; включить после установки choosenim
- ~~winfetch~~ — Апстрим Windows-only ('Only supported on Windows'). На Linux используйте fastfetch/macchina
- ~~lifecycler~~ — Апстрим недоступен (404) / пакет удалён из registry
- ~~shuffle~~ — причина не указана
- ~~weatherspect~~ — причина не указана
- ~~termdvd~~ — Апстрим недоступен (404) / пакет удалён из registry
- ~~fireworks~~ — Источник недоступен с этой сети (archive.org/sourceforge); включить при смене сети
- ~~bb~~ — Источник недоступен с этой сети (archive.org/sourceforge); включить при смене сети
- ~~cli-visualizer~~ — Апстрим недоступен (404) / пакет удалён из registry
- ~~chucknorris~~ — Апстрим-слаг не найден, пакет отключён до уточнения
- ~~hack~~ — Апстрим-слаг не найден, пакет отключён до уточнения
- ~~WezTerm~~ — Сборка ~40+ мин, может не собраться на s390x/ppc64le
- ~~Ghostty~~ — Требуется zig, которого нет в Fedora; собирать вручную или из COPR pgdev
- ~~eDEX-UI~~ — Electron, огромная сборка; проще flathub
- ~~taskwarrior-tui~~ — Требует taskwarrior, которого нет в Fedora — собрать оба слишком дорого
