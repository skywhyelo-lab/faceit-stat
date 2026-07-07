# 🤖 Faceit Stats Analyzer Bot - Инструкция по запуску

## ⚙️ Требования

- Python 3.10+
- pip (встроен в Python)
- Telegram Bot Token
- Faceit API Key

---

## 📦 Установка зависимостей

```bash
pip install python-telegram-bot aiohttp matplotlib
```

**Или в одной строке:**
```bash
pip install python-telegram-bot==21.0 aiohttp==3.9.1 matplotlib==3.8.4
```

---

## 🔑 Получение токенов

### 1️⃣ Telegram Bot Token

1. Открой Telegram и найди бота **@BotFather**
2. Напиши `/start` → `/newbot`
3. Дай имя боту (например: `Faceit Stats Analyzer`)
4. Дай юзернейм (например: `faceit_stats_bot_xyz`)
5. Скопируй полученный токен: `123456:ABCDefGHIJKLMNOpqrstuVWXYZ`

### 2️⃣ Faceit API Key (ВАЖНО: ПОМЕНЯЙ ПОСЛЕ СОЗДАНИЯ БОТА!)

1. Зайди на https://www.faceit.com/en/settings/account
2. Прокрути вниз → найди **API** или **Developer**
3. Нажми **Generate API Key**
4. Скопируй ключ

**⚠️ БЕЗОПАСНОСТЬ:** После создания бота **регенерируй ключ** в настройках Faceit!
```bash
# После создания бота поменяй ключ на новый
```

---

## 🚀 Запуск

### Способ 1: Через переменные окружения (рекомендуется)

```bash
export BOT_TOKEN="123456:ABCDefGHIJKLMNOpqrstuVWXYZ"
export FACEIT_API_KEY="faa2d51c-d11e-431f-a20a-ddec6f8d7f41"
python faceit_analyzer_bot.py
```

### Способ 2: На Windows (PowerShell)

```powershell
$env:BOT_TOKEN="123456:ABCDefGHIJKLMNOpqrstuVWXYZ"
$env:FACEIT_API_KEY="faa2d51c-d11e-431f-a20a-ddec6f8d7f41"
python faceit_analyzer_bot.py
```

### Способ 3: Отредактировать скрипт вручную

Открой `faceit_analyzer_bot.py` и найди:
```python
FACEIT_API_KEY = os.getenv('FACEIT_API_KEY', 'YOUR_API_KEY_HERE')
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
```

Замени на:
```python
FACEIT_API_KEY = "faa2d51c-d11e-431f-a20a-ddec6f8d7f41"
BOT_TOKEN = "123456:ABCDefGHIJKLMNOpqrstuVWXYZ"
```

---

## 📱 Использование в Telegram

После запуска бота:

1. Найди его по юзернейму (например `@faceit_stats_bot_xyz`)
2. Напиши `/start`

### Команды:

- `/start` - главное меню
- `/analyze` - начать анализ (интерактивный режим)
- `/compare nickname1 nickname2` - быстро сравнить двух игроков
  
  Пример:
  ```
  /compare skywhyelo romanch1k
  ```

### Интерактивный анализ:

1. Нажми кнопку "📊 Анализировать"
2. Введи ник первого игрока (или ссылку)
3. Введи ник второго игрока
4. Получи полный отчет + график

---

## 📊 Что показывает бот

✅ **K/D Ratio** - отношение убийств к смертям
✅ **Headshot %** - процент выстрелов в голову
✅ **Win Rate** - процент выигранных матчей
✅ **Статистика по картам** - WR на каждой карте
✅ **Рекомендации** - советы по улучшению
✅ **График сравнения** - наглядная визуализация
✅ **История анализов** - отслеживание прогресса

---

## 🗄️ База данных

Все анализы сохраняются в **`faceit_stats.db`** (SQLite):
- Автоматически создается при первом запуске
- Хранит историю всех анализов
- Позволяет отслеживать прогресс игроков

---

## ⚠️ Возможные проблемы

### "Invalid API Key"
- Проверь, что ключ скопирован правильно (без пробелов)
- Регенерируй ключ в настройках Faceit

### "Player not found"
- Проверь написание ника (чувствительно к регистру НЕ)
- На Faceit может быть несколько игроков с похожими никамы

### "Connection refused"
- Проверь интернет
- Убедись, что сервер Faceit доступен

### Бот не отвечает
- Перезагрузи бота (Ctrl+C, затем python скрипт)
- Проверь логи консоли на ошибки

---

## 🔒 Безопасность

**ВАЖНО:**
1. Не публикуй API Key и Bot Token в открытый доступ
2. Используй переменные окружения, а не hardcode в коде
3. После использования в публичном месте - регенерируй ключи
4. Если случайно выложил токен - сразу отключи его в @BotFather

---

## 📝 Структура файлов

```
.
├── faceit_analyzer_bot.py  ← Основной скрипт бота
├── SETUP.md                ← Эта инструкция
└── faceit_stats.db         ← БД (создается автоматически)
```

---

## 🚀 Для развертывания на сервере

Если хочешь запускать бота 24/7:

### На Linux (Systemd)

Создай файл `/etc/systemd/system/faceit-bot.service`:
```ini
[Unit]
Description=Faceit Stats Analyzer Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/bot
Environment="BOT_TOKEN=YOUR_TOKEN"
Environment="FACEIT_API_KEY=YOUR_API_KEY"
ExecStart=/usr/bin/python3 /path/to/bot/faceit_analyzer_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable faceit-bot
sudo systemctl start faceit-bot
```

---

## ✅ Готово!

Если все установил правильно - бот готов к работе! 🎮
