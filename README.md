# Telegram Account Manager

Платформа для управления несколькими Telegram-аккаунтами: Telegram-бот (aiogram) и web-панель (FastAPI + React).

## Возможности

- Добавление и управление Telegram-аккаунтами (код + 2FA)
- Шифрование сессий (Fernet)
- Массовые рассылки с настраиваемыми интервалами
- Web-панель: чаты, сообщения, рассылки, история
- Статистика отправок и обработка flood-wait

## Архитектура

```
┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│ Telegram Bot │     │  Web (React) │     │   SQLite    │
│   main.py    │     │  run_web.py  │     │  data/      │
└──────┬───────┘     └──────┬───────┘     └──────▲──────┘
       │                    │                    │
       └──────────┬─────────┴────────────────────┘
                  ▼
           tam/services/
         (AccountManager, MessageSender)
                  │
                  ▼
              Telethon
```

## Структура проекта

```
├── tam/                    # Ядро приложения
│   ├── config.py           # Настройки и валидация
│   ├── db/                 # SQLAlchemy модели и Database
│   ├── services/           # AccountManager, MessageSender
│   ├── telegram/           # Сериализация Telethon → JSON
│   └── bot/                # aiogram handlers, keyboards
├── web/                    # FastAPI backend
│   ├── routes/             # API endpoints
│   ├── auth.py             # JWT авторизация
│   └── security.py         # Rate limit, безопасные ошибки
├── frontend/               # React + Vite SPA
├── scripts/generate_key.py # Генерация ENCRYPTION_KEY
├── main.py                 # Запуск Telegram-бота
├── run_web.py              # Запуск web-платформы
├── Dockerfile              # Multi-stage: bot / web
└── docker-compose.yml      # Профили bot и web
```

## Требования

- Python 3.11+
- Node.js 20+ (для сборки frontend)
- [uv](https://docs.astral.sh/uv/) или pip
- Telegram Bot Token, API ID/Hash с [my.telegram.org](https://my.telegram.org)

---

## Развертывание

### 1. Подготовка окружения

```bash
git clone https://github.com/Justhateme0/Telegram-Account-Manager-Bot
cd Telegram-Account-Manager-Bot
cp .env.example .env
```

Заполните `.env`:

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен от [@BotFather](https://t.me/botfather) (для бота) |
| `API_ID`, `API_HASH` | Credentials с [my.telegram.org](https://my.telegram.org) |
| `ENCRYPTION_KEY` | `uv run python scripts/generate_key.py` |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `WEB_PASSWORD` | Надёжный пароль панели (≥8 символов) |
| `WEB_SECRET` | Случайная строка ≥32 символов для JWT |
| `WEB_HOST` | `127.0.0.1` локально, `0.0.0.0` в Docker |
| `WEB_PORT` | Порт web-панели (по умолчанию `8080`) |

Для **локальной разработки** можно временно добавить `ALLOW_INSECURE=true` — отключает проверку слабых паролей. **Не используйте в production.**

### 2. Web-платформа (рекомендуется)

```bash
# Python-зависимости
uv sync
# или: pip install -r requirements.txt

# Сборка frontend
cd frontend && npm ci && npm run build && cd ..

# Запуск
uv run python run_web.py
```

Откройте `http://127.0.0.1:8080` и войдите паролем из `WEB_PASSWORD`.

#### Разработка frontend

```bash
# Терминал 1 — backend
uv run python run_web.py

# Терминал 2 — Vite dev-сервер
cd frontend && npm run dev
```

Открывайте **`http://127.0.0.1:5173`** (не `localhost`, если VPN блокирует loopback).

API-документация: `http://127.0.0.1:8080/docs`

### 3. Telegram-бот

```bash
uv sync
uv run python main.py
```

Бот принимает команды только от пользователей из `ADMIN_IDS`.

### 4. Docker

**Web-платформа** (frontend собирается внутри образа):

```bash
docker compose --profile web up -d --build
```

**Только бот:**

```bash
docker compose --profile bot up -d --build
```

Данные сохраняются в `./data` и `./sessions`.

### 5. Production за reverse-proxy

Пример nginx перед web-платформой:

```nginx
server {
    listen 443 ssl http2;
    server_name panel.example.com;

    ssl_certificate     /etc/letsencrypt/live/panel.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/panel.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Рекомендации для production:

- `WEB_HOST=127.0.0.1` — слушать только localhost, nginx терминирует TLS
- `WEB_CORS_ORIGINS=https://panel.example.com` — только ваш домен
- `WEB_PASSWORD` и `WEB_SECRET` — уникальные, длинные значения
- `ALLOW_INSECURE=false` (или не задавать)
- Ограничьте доступ к серверу файрволом
- Регулярно делайте бэкап `./data/bot.db`

---

## Безопасность

| Мера | Описание |
|------|----------|
| ACL бота | Только `ADMIN_IDS` могут пользоваться ботом |
| JWT | Web API защищён Bearer-токеном (24 ч) |
| Rate limit | 5 неудачных попыток входа / 15 мин с IP |
| Timing-safe | Сравнение пароля через `secrets.compare_digest` |
| Шифрование | Telethon-сессии в БД зашифрованы Fernet |
| CORS | Явный whitelist origins, ограниченные методы/заголовки |
| Ошибки API | Внутренние исключения Telegram не утекают клиенту |

---

## Использование бота

- `/start` — главное меню
- `📱 Аккаунты` — добавление и список аккаунтов
- `✉️ Сообщения` — создание рассылки
- `📊 Статистика` / `📜 История` — аналитика

Markdown в сообщениях: `**жирный**`, `*курсив*`, `` `код` ``, `[ссылка](url)`.

---

## Технологии

| Слой | Стек |
|------|------|
| Bot | aiogram 3.3, Telethon 1.34 |
| Web API | FastAPI, uvicorn, python-jose |
| Frontend | React 18, TypeScript, Vite 5 |
| DB | SQLAlchemy 2.0 + aiosqlite |
| Crypto | cryptography (Fernet) |

---

## Ограничения

- Соблюдайте лимиты Telegram API и ToS
- Минимальный интервал между сообщениями — 10+ секунд
- `PendingAuthStore` хранится в памяти процесса (не для multi-worker)

---

**Важно:** используйте платформу ответственно. Разработчик не несёт ответственности за блокировку аккаунтов при нарушении правил Telegram.
