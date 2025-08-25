import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from openai import AsyncOpenAI
from config import Config

logger = logging.getLogger(__name__)


class CommunicationAnalyzer:
    """AI-powered communication analyzer using OpenAI API"""

    def __init__(self):
        # Using gpt-4o model as requested
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = "gpt-4o"

    async def analyze_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Analyze communication messages and return structured report

        Args:
            messages: List of message dictionaries with keys: username, text, timestamp

        Returns:
            Formatted analysis report as string
        """
        if not messages:
            return "❌ Нет сообщений для анализа."

        try:
            # Prepare messages for analysis
            formatted_messages = self._format_messages(messages)

            # Create analysis prompt
            analysis_prompt = self._create_analysis_prompt(
                formatted_messages, len(messages))

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse response
            response_content = response.choices[0].message.content
            if not response_content:
                return "❌ Получен пустой ответ от AI."

            analysis_json = json.loads(response_content)

            # Format final report
            return self._format_analysis_report(analysis_json, len(messages))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return "❌ Ошибка обработки ответа AI. Попробуйте позже."
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return f"❌ Ошибка при анализе: {str(e)}"

    async def analyze_user_communication(
        self,
        user_messages: List[Dict[str, Any]],
        interactions: Dict[str, List[Dict[str, Any]]],
        username: str,
    ) -> str:
        """
        Analyze individual user's communication patterns and interactions

        Args:
            user_messages: List of messages from the target user
            interactions: Dict of interaction partners and their message exchanges
            username: Username of the analyzed user

        Returns:
            Formatted personal analysis report as string
        """
        if not user_messages:
            return "❌ Нет сообщений пользователя для анализа."

        try:
            # Create personal analysis prompt
            analysis_prompt = self._create_personal_analysis_prompt(
                user_messages, interactions, username)

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_personal_analysis_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=3000,
            )

            # Parse response
            response_content = response.choices[0].message.content
            if not response_content:
                return "❌ Получен пустой ответ от AI."

            analysis_json = json.loads(response_content)

            # Format final report
            return self._format_personal_analysis_report(
                analysis_json, username, len(user_messages))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return "❌ Ошибка обработки ответа AI. Попробуйте позже."
        except Exception as e:
            logger.error(f"Personal analysis failed: {e}")
            return f"❌ Ошибка при анализе: {str(e)}"

    def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for AI analysis"""
        formatted = []
        for msg in messages:
            ts = msg.get("timestamp")
            if hasattr(ts, "strftime"):
                timestamp = ts.strftime("%Y-%m-%d %H:%M")
            else:
                timestamp = str(ts)
            username = msg.get("username", "unknown")
            text = msg.get("text", "")
            formatted.append(f"[{timestamp}] {username}: {text}")
        return "\n".join(formatted)

    def _get_system_prompt(self) -> str:
        """Get system prompt for group chat communication analysis"""
        return (
            "Ты — AI-ассистент и коуч по коммуникациям, анализирующий рабочие групповые чаты.\n\n"
            "Руководствуйся принципами качественной обратной связи (ОС):\n"
            "- Своевременность: анализируй актуальные события.\n"
            "- Непубличность: избегай персональных ярлыков; оценивай сообщения и паттерны, а не личности.\n"
            "- Ясность: формулируй просто и конкретно.\n"
            "- Опора на факты: используй наблюдаемые признаки и цитаты как примеры, без эмоций и оценок личности.\n"
            "- Конструктивность: предлагай практические шаги улучшения.\n\n"
            "Фокус:\n"
            "- Тон и стиль общения\n"
            "- Эффективность передачи информации\n"
            "- Конструктивность диалогов\n"
            "- Общая атмосфера в команде\n\n"
            "Ответь ТОЛЬКО в JSON со следующими полями:\n"
            "{\n"
            '  "communication_tone": "краткое описание общего тона",\n'
            '  "effectiveness_score": число от 1 до 10,\n'
            '  "positive_patterns": ["список позитивных паттернов (с фактами/примерами)"],\n'
            '  "improvement_areas": ["список областей для улучшения (без ярлыков, с фокусом на действия)"],\n'
            '  "recommendations": ["конкретные рекомендации по улучшению"],\n'
            '  "team_atmosphere": "описание атмосферы в команде"\n'
            "}\n"
            "Будь объективным, избегай оценок личности, опирайся на наблюдаемые факты и ориентируйся на улучшение процессов."
        )

    def _create_analysis_prompt(self, formatted_messages: str,
                                message_count: int) -> str:
        """Create analysis prompt with messages"""
        return (
            f"Проанализируй следующие {message_count} сообщений из рабочего чата и предоставь структурированный анализ "
            "коммуникации по принципам качественной ОС (своевременность, непубличность, ясность, факты, конструктивность).\n\n"
            f"{formatted_messages}\n\n"
            "Выдели паттерны коммуникации и дай объективную оценку с практическими рекомендациями."
        )

    def _format_analysis_report(self, analysis: Dict[str, Any],
                                message_count: int) -> str:
        """Format group analysis results into readable report"""
        report = f"""📊 **Анализ {message_count} сообщений**

🎯 **Общий тон коммуникации:**
{analysis.get('communication_tone', 'Не определен')}

📈 **Оценка эффективности:** {analysis.get('effectiveness_score', 'N/A')}/10

✅ **Позитивные паттерны:**"""

        for pattern in analysis.get("positive_patterns", []):
            report += f"\n-  {pattern}"

        report += "\n\n🔧 **Области для улучшения:**"
        for area in analysis.get("improvement_areas", []):
            report += f"\n-  {area}"

        report += "\n\n💡 **Рекомендации:**"
        for rec in analysis.get("recommendations", []):
            report += f"\n-  {rec}"

        report += f"\n\n🌟 **Атмосфера в команде:**\n{analysis.get('team_atmosphere', 'Не определена')}"
        report += f"\n\n---\n📅 Анализ выполнен: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        return report

    def _get_personal_analysis_system_prompt(self) -> str:
        """Get system prompt for personal communication analysis (enhanced with feedback methodology)"""
        return (
            "Ты — AI-ассистент, эксперт по коммуникациям, который анализирует стиль общения конкретного пользователя в групповом чате "
            "и предоставляет ему персональную, конструктивную обратную связь (ОС).\n\n"
            "КОНТЕКСТ: ПРИНЦИПЫ КАЧЕСТВЕННОЙ ОБРАТНОЙ СВЯЗИ (ОС)\n"
            "Держись пяти критериев: своевременность, непубличность (похвала может быть публичной), ясность, опора на факты, конструктивность. "
            "Используй конкретные примеры и цитаты как доказательства. Избегай оценок личности; описывай наблюдаемое поведение, его эффект и пути улучшения. "
            "Различай виды ОС: мотивирующая (закрепляет успех), корректирующая (исправляет ошибки), развивающая (помогает расти по запросу).\n\n"
            "Структура ОС: описание ДЕЙСТВИЯ/ситуации → ПОСЛЕДСТВИЯ/результат → ВОПРОС для рефлексии → ДОГОВОРЕННОСТЬ/шаги.\n\n"
            "Ответь ТОЛЬКО в JSON по схеме:\n"
            "{\n"
            '  "overall_summary": "краткий общий вывод о стиле",\n'
            '  "personal_style": "описание индивидуального стиля общения",\n'
            '  "communication_effectiveness": число от 1 до 10,\n'
            '  "motivating_feedback": [\n'
            '    {"quote": "цитата/пример", "context": "кратко о ситуации", "positive_result": "какой эффект это дало"}\n'
            "  ],\n"
            '  "development_feedback": [\n'
            '    {"quote": "цитата/пример", "action": "что сделал/сказал", "potential_consequences": "к чему привело/могло привести", '
            '"reflection_question": "открытый вопрос для осмысления", "improvement_suggestion": "как сформулировать/действовать иначе"}\n'
            "  ],\n"
            '  "strengths": ["ключевые сильные стороны"],\n'
            '  "growth_areas": ["зоны для развития (поведенческие, не личностные ярлыки)"],\n'
            '  "interaction_patterns": {"partner_name": "особенности взаимодействия с этим человеком"},\n'
            '  "recommendations": ["1–3 практических шага на будущее"],\n'
            '  "agreements": ["если уместно: зафиксированные договоренности/следующие шаги"]\n'
            "}\n"
            "Будь уважительным, точным, поддерживающим и сфокусированным на росте."
        )

    def _create_personal_analysis_prompt(
        self,
        user_messages: List[Dict[str, Any]],
        interactions: Dict[str, List[Dict[str, Any]]],
        username: str,
    ) -> str:
        """Create enhanced personal analysis prompt with examples and structure"""

        # Format user's own messages (last 20)
        user_msgs_formatted = []
        for msg in user_messages[-20:]:
            ts = msg.get("timestamp")
            if hasattr(ts, "strftime"):
                timestamp = ts.strftime("%Y-%m-%d %H:%M")
            else:
                timestamp = str(ts)
            text = msg.get("text", "")
            user_msgs_formatted.append(f"[{timestamp}] {text}")

        # Format interactions with different partners (last 5 per partner)
        interactions_formatted = []
        for partner, msgs in interactions.items():
            if partner == "self":
                continue
            if msgs:
                interactions_formatted.append(
                    f"\n--- Взаимодействие с {partner} ---")
                for interaction in msgs[-5:]:
                    if interaction.get("type") == "interaction":
                        partner_msg = interaction.get("partner_message", {})
                        user_msg = interaction.get("user_message")
                        p_ts = partner_msg.get("timestamp")
                        if hasattr(p_ts, "strftime"):
                            p_time = p_ts.strftime("%Y-%m-%d %H:%M")
                        else:
                            p_time = str(p_ts)
                        interactions_formatted.append(
                            f"[{p_time}] {partner}: {partner_msg.get('text', '')}"
                        )
                        if user_msg:
                            u_ts = user_msg.get("timestamp")
                            if hasattr(u_ts, "strftime"):
                                u_time = u_ts.strftime("%Y-%m-%d %H:%M")
                            else:
                                u_time = str(u_ts)
                            interactions_formatted.append(
                                f"[{u_time}] {username}: {user_msg.get('text', '')}"
                            )

        prompt = (
            f"Проанализируй персональный стиль коммуникации пользователя {username} на основе его сообщений и взаимодействий.\n\n"
            "ДАННЫЕ\n"
            "=== СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ ===\n"
            f"{chr(10).join(user_msgs_formatted)}\n\n"
            "=== ВЗАИМОДЕЙСТВИЯ С ДРУГИМИ ===\n"
            f"{chr(10).join(interactions_formatted)}\n\n"
            "ЗАДАЧА\n"
            f"1) Опиши индивидуальный стиль общения пользователя {username}\n"
            "2) Как он взаимодействует с разными собеседниками\n"
            "3) Коммуникативные сильные стороны и зоны роста\n"
            "4) Паттерны поведения в различных ситуациях\n"
            "5) Сформируй персональную ОС по структуре: действие → последствия/результат → вопрос → договоренность/шаги.\n\n"
            "Верни ответ строго в JSON по схеме, указанной в системной инструкции."
        )
        return prompt

    def _format_personal_analysis_report(self, analysis: Dict[str, Any],
                                         username: str,
                                         message_count: int) -> str:
        """Format personal analysis results into readable report"""
        report = f"""👤 **Персональный анализ для @{username}**

📊 Проанализировано {message_count} сообщений

🧭 **Общий вывод:**
{analysis.get('overall_summary', 'Не определен')}

🎯 **Ваш стиль коммуникации:**
{analysis.get('personal_style', 'Не определен')}

📈 **Эффективность коммуникации:** {analysis.get('communication_effectiveness', 'N/A')}/10
"""

        strengths = analysis.get("strengths", [])
        if strengths:
            report += "\n✅ **Сильные стороны:**"
            for s in strengths:
                report += f"\n-  {s}"

        # Motivating feedback section
        motivating = analysis.get("motivating_feedback", [])
        if motivating:
            report += "\n\n🌟 **Мотивирующая ОС (что стоит закрепить):**"
            for item in motivating:
                quote = item.get("quote")
                ctx = item.get("context")
                result = item.get("positive_result")
                line = "-  "
                if quote:
                    line += f"«{quote}»"
                if ctx:
                    line += f" — контекст: {ctx}"
                if result:
                    line += f" — результат: {result}"
                report += f"\n{line}"

        # Development/corrective feedback
        development = analysis.get("development_feedback", [])
        if development:
            report += "\n\n🛠️ **Зоны для развития (корректирующая/развивающая ОС):**"
            for item in development:
                quote = item.get("quote")
                action = item.get("action")
                cons = item.get("potential_consequences")
                question = item.get("reflection_question")
                suggestion = item.get("improvement_suggestion")

                if quote or action:
                    report += "\n-  Ситуация:"
                    if quote:
                        report += f" «{quote}»"
                    if action:
                        report += f" | Действие: {action}"
                if cons:
                    report += f"\n  Последствия/риск: {cons}"
                if question:
                    report += f"\n  Вопрос для рефлексии: {question}"
                if suggestion:
                    report += f"\n  Альтернатива: {suggestion}"

        # Interaction patterns
        interaction_patterns = analysis.get("interaction_patterns", {})
        if interaction_patterns:
            report += "\n\n🤝 **Особенности взаимодействия:**"
            for partner, pattern in interaction_patterns.items():
                report += f"\n-  С {partner}: {pattern}"

        # Recommendations and agreements
        recs = analysis.get("recommendations", [])
        if recs:
            report += "\n\n💡 **Практические рекомендации:**"
            for rec in recs:
                report += f"\n-  {rec}"

        agreements = analysis.get("agreements", [])
        if agreements:
            report += "\n\n📝 **Договоренности/следующие шаги:**"
            for agr in agreements:
                report += f"\n-  {agr}"

        report += f"\n\n---\n📅 Персональный анализ выполнен: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        report += "\n🔒 Этот отчет конфиденциален и отправлен только вам."

        return report
