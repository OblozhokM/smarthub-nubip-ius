# ІУС «SmartHub NUBiP»

Інформаційно-управлінська система «SmartHub NUBiP» — навчальний проєкт Telegram-бота для моніторингу та керування показниками «розумного» хабу. Система поєднує Telegram-інтерфейс, HTTP-ingest для отримання даних від датчиків, симулятор показників, вебдашборд для перегляду стану системи та набір автоматизованих тестів.

## Можливості

- Telegram-бот на базі `aiogram` для взаємодії з користувачем.
- Приймання показників датчиків через HTTP-ingest (`aiohttp`).
- Симулятор генерації та надсилання показників (`simulator.py`).
- Вебдашборд для перегляду поточних значень та графіків.
- Зберігання даних у локальному JSON-сховищі.
- Імпорт бронювань із CSV.
- Автоматизовані тести на `pytest`.

## Структура проєкту

```text
smarthub-nubip-ius/
├── .gitignore
├── LICENSE
├── README.md
└── my_bot/
    ├── .env.example
    ├── alerts.py
    ├── bot.py
    ├── broadcast.py
    ├── check_broadcast.py
    ├── check_chart.py
    ├── check_dashboard.py
    ├── check_dashboard_appendix.py
    ├── check_simulator.py
    ├── check_stream.py
    ├── check_weather.py
    ├── config.py
    ├── dashboard.py
    ├── dashboard_appendix.py
    ├── data/
    │   └── .gitkeep
    ├── handlers/
    │   ├── __init__.py
    │   ├── booking.py
    │   ├── check.py
    │   └── common.py
    ├── import/
    │   └── bookings.csv
    ├── ingest.py
    ├── keyboards.py
    ├── main.py
    ├── middlewares/
    │   ├── __init__.py
    │   └── throttling.py
    ├── pytest.ini
    ├── requirements.txt
    ├── scheduler.py
    ├── seed.py
    ├── seed_chart.py
    ├── serve_dashboard.py
    ├── simulator.py
    ├── states.py
    ├── storage.py
    ├── tests/
    │   ├── conftest.py
    │   ├── test_bookings.py
    │   ├── test_chart.py
    │   ├── test_dashboard.py
    │   ├── test_ingest.py
    │   ├── test_storage.py
    │   └── test_validators.py
    ├── utils/
    │   ├── chart.py
    │   ├── csv_parser.py
    │   ├── format.py
    │   ├── outbox.py
    │   ├── png.py
    │   ├── signal.py
    │   ├── stats.py
    │   └── validators.py
    └── weather.py
```

## Вимоги

- Python 3.11+ (рекомендовано)
- pip
- Віртуальне середовище Python

## Встановлення та запуск

1. Клонуйте репозиторій:

```bash
git clone https://github.com/OblozhokM/smarthub-nubip-ius.git
cd smarthub-nubip-ius/my_bot
```

2. Створіть та активуйте віртуальне середовище:

```bash
python -m venv venv
```

Для Windows (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
```

Для Linux/macOS:

```bash
source venv/bin/activate
```

3. Встановіть залежності:

```bash
pip install -r requirements.txt
```

4. Налаштуйте змінні середовища:

```bash
cp .env.example .env
```

Для Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Заповніть `.env` власними значеннями:

```env
BOT_TOKEN=your_bot_token
INGEST_KEY=your_ingest_key
DASHBOARD_TOKEN=your_dashboard_token
INGEST_HOST=127.0.0.1
INGEST_PORT=3000
```

5. Запустіть бота:

```bash
python main.py
```

6. У окремому терміналі запустіть симулятор датчиків (за потреби):

```bash
python simulator.py
```

## Запуск тестів

Запуск усіх тестів:

```bash
pytest -q
```

Перевірка дашборду:

```bash
python check_dashboard.py
```

## Змінні середовища

| Змінна | Опис |
| --- | --- |
| `BOT_TOKEN` | Токен Telegram-бота від BotFather |
| `INGEST_KEY` | Ключ авторизації для HTTP-ingest |
| `DASHBOARD_TOKEN` | Токен доступу до вебдашборду |
| `INGEST_HOST` | Хост ingest-сервера (за замовчуванням `127.0.0.1`) |
| `INGEST_PORT` | Порт ingest-сервера (за замовчуванням `3000`) |

## Ліцензія

Цей проєкт розповсюджується за ліцензією MIT. Деталі див. у файлі [LICENSE](LICENSE).
