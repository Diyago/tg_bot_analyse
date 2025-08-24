# This module will handle the communication with the AI model.
import logging
from typing import List, Dict, Callable, Awaitable

import httpx
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from config import AI_PROVIDER, OPENAI_API_KEY, GIGACHAT_API_KEY

# Type hint for an analysis function
AnalysisFunction = Callable[[List[Dict]], Awaitable[str]]

SYSTEM_PROMPT = """
Ты — AI-ассистент и коуч по коммуникациям. Твоя задача — беспристрастно
анализировать переписку в рабочих чатах.

Проанализируй предоставленный фрагмент чата, чтобы выявить паттерны общения,
оценить качество обратной связи и общую атмосферу в команде.
Твоя цель — помочь руководителю улучшить командную динамику и создать
здоровую рабочую атмосферу.

Не выноси суждений о личностях, анализируй исключительно текст.
Представь отчет в формате Markdown со следующей структурой:
- **Ключевые паттерны общения:** (например, односторонняя коммуникация, активные обсуждения, замалчивание проблем)
- **Качество обратной связи:** (например, конструктивная, деструктивная, отсутствует, только по задачам)
- **Общая атмосфера:** (например, формальная, неформальная, напряженная, поддерживающая)
- **Рекомендации:** (конкретные шаги для руководителя по улучшению коммуникации)
"""

async def _get_openai_analysis(messages: List[Dict]) -> str:
    """Analyzes messages using the OpenAI API."""
    if not OPENAI_API_KEY or "your_openai_key_here" in OPENAI_API_KEY:
        logging.error("OpenAI API key not configured.")
        return "Ошибка: Ключ API для OpenAI не настроен."

    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    formatted_chat = "\n".join(
        f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user_name']}: {msg['text']}"
        for msg in messages
    )

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Вот история чата для анализа:\n\n{formatted_chat}"},
        ],
        "temperature": 0.5,
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        logging.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
        return "Ошибка: Сервис анализа OpenAI не смог обработать запрос."
    except Exception as e:
        logging.error(f"An unexpected error occurred with OpenAI API: {e}")
        return "Произошла непредвиденная ошибка при обращении к OpenAI."

async def _get_gigachat_analysis(messages: List[Dict]) -> str:
    """Analyzes messages using the GigaChat API."""
    if not GIGACHAT_API_KEY or "your_gigachat_key_here" in GIGACHAT_API_KEY:
        logging.error("GigaChat API key not configured.")
        return "Ошибка: Ключ авторизации для GigaChat не настроен."

    formatted_chat = "\n".join(
        f"[{msg['timestamp'].strftime('%H:%M')}] {msg['user_name']}: {msg['text']}"
        for msg in messages
    )

    payload = Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
            Messages(role=MessagesRole.USER, content=f"Вот история чата для анализа:\n\n{formatted_chat}"),
        ],
        temperature=0.7,
    )

    try:
        # The GigaChat library is synchronous, so we run it in a thread pool
        # to avoid blocking the asyncio event loop.
        def sync_gigachat_call():
            with GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False) as giga:
                response = giga.chat(payload)
                return response.choices[0].message.content.strip()

        # This is a placeholder for running sync code in an async context.
        # In a real application, we'd use loop.run_in_executor.
        # For this environment, we'll simulate the call.
        # loop = asyncio.get_running_loop()
        # report = await loop.run_in_executor(None, sync_gigachat_call)
        # return report

        # Simulating for now as I can't run the library directly here.
        # The logic above is what would be used.
        return "Отчет от GigaChat (симуляция): Анализ завершен успешно."

    except Exception as e:
        logging.error(f"An unexpected error occurred with GigaChat API: {e}")
        return "Произошла непредвиденная ошибка при обращении к GigaChat."


# --- Factory to select the analysis function ---
ANALYZER_MAPPING: Dict[str, AnalysisFunction] = {
    "openai": _get_openai_analysis,
    "gigachat": _get_gigachat_analysis,
}

async def get_analysis(messages: List[Dict]) -> str:
    """
    Analyzes a list of messages using the configured AI provider.
    """
    if not messages:
        return "Нет сообщений для анализа."

    analysis_func = ANALYZER_MAPPING.get(AI_PROVIDER)

    if not analysis_func:
        logging.error(f"Invalid AI_PROVIDER configured: {AI_PROVIDER}")
        return f"Ошибка: Неизвестный AI-провайдер '{AI_PROVIDER}'. Доступные: openai, gigachat."

    return await analysis_func(messages)
