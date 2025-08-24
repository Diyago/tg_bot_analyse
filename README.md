# Communication Coach Telegram Bot

Этот Telegram-бот выступает в роли AI-ассистента и коуча по коммуникациям, специализирующегося на анализе рабочих чатов. Он помогает руководителям улучшать командную динамику, повышать качество обратной связи и создавать здоровую рабочую атмосферу.

## Features

- **Анализ по требованию**: Бот анализирует переписку только по команде от администратора чата.
- **Конфиденциальность**: Отчет об анализе отправляется в личные сообщения администратору, вызвавшему команду, и никогда не публикуется в общем чате.
- **Поддержка нескольких AI-провайдеров**: Вы можете выбрать между OpenAI и GigaChat для анализа сообщений.
- **Простота использования**: Достаточно добавить бота в чат и использовать простые команды.
- **Гибкая настройка**: Все ключевые параметры (токены, AI-провайдер) настраиваются через переменные окружения.

## Setup and Installation

Для запуска бота вам понадобится Python 3.10 или выше.

1.  **Клонируйте репозиторий:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Создайте и активируйте виртуальное окружение:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Для Windows: venv\Scripts\activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Все настройки бота хранятся в файле `.env`. Создайте этот файл в корне проекта, скопировав `.env.example` (если он есть) или создав его с нуля.

**Содержимое файла `.env`:**

```ini
# --- Telegram Bot Configuration ---
# Получите этот токен у @BotFather в Telegram
TELEGRAM_BOT_TOKEN="your_token_here"

# --- AI Configuration ---
# Укажите AI-провайдера: 'openai' или 'gigachat'
AI_PROVIDER="openai"

# API Ключи - заполните ключ для выбранного провайдера
OPENAI_API_KEY="your_openai_key_here"
GIGACHAT_API_KEY="your_gigachat_key_here"
```

### Описание переменных:

-   `TELEGRAM_BOT_TOKEN`: Уникальный токен вашего Telegram-бота.
-   `AI_PROVIDER`: Определяет, какой сервис будет использоваться для анализа. Установите `openai` или `gigachat`.
-   `OPENAI_API_KEY`: Ваш ключ API от OpenAI (если используете `openai`).
-   `GIGACHAT_API_KEY`: Ваш ключ авторизации от GigaChat (если используете `gigachat`).

## Running the Bot

После установки зависимостей и настройки файла `.env`, запустите бота командой:

```bash
python main.py
```

Бот начнет работать и будет готов к добавлению в групповые чаты.

## Deployment

Для постоянной работы бота рекомендуется развернуть его на сервере (VPS).

Один из надежных способов — использовать `systemd` для управления процессом бота.

1.  **Создайте service-файл** (например, `/etc/systemd/system/telegram_coach_bot.service`):
    ```ini
    [Unit]
    Description=Communication Coach Telegram Bot
    After=network.target

    [Service]
    User=your_user
    Group=your_group
    WorkingDirectory=/path/to/your/bot/directory
    ExecStart=/path/to/your/bot/directory/venv/bin/python main.py
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```
    - Замените `your_user`, `your_group` и пути на актуальные.

2.  **Запустите и активируйте сервис:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start telegram_coach_bot.service
    sudo systemctl enable telegram_coach_bot.service
    ```

Вы также можете использовать Docker для контейнеризации приложения, что упростит развертывание и управление зависимостями.
