# meta developer: @mlwdev
# scope: hikka_only

import logging
import g4f
import asyncio

from .. import loader, utils
from telethon.tl.types import Message, UserPremium

logger = logging.getLogger(__name__)


@loader.tds
class G4fAskMod(loader.Module):
    """Модуль для взаимодействия с ИИ моделями через g4f"""
    strings = {
        "name": "G4fAsk",
        "no_args_ai": "❓ **Usage:** `.ai <model_alias>`\n**Available:** `{}`\n**Current:** `{}`",
        "invalid_model": "❌ Invalid model alias `{}`. Available: {}",
        "model_set": "✅ AI model set to `{}`.",
        "no_args_ask": "❓ Please provide a question. Usage: `.ask <query>`",
        "thinking": "🧠 Thinking with `{}`...",
        "result": "❓ Question:\n{}\n\n💡 Answer ({}):\n{}",
        "missing_dep": "❌ **Error:** Missing dependency. Please install required packages (`pip install -U g4f`).",
        "request_error": "❌ **Error:** Failed to get response from `{}`. ({})",
        "unexpected_error": "❌ **Error:** An unexpected error occurred while contacting `{}`. Error: {}",
    }
    strings_ru = {
        "_cls_doc": "Модуль для взаимодействия с ИИ моделями через g4f",
        "no_args_ai": "❓ **Использование:** `.ai <модель>`\n**Доступные:** `{}`\n**Текущая:** `{}`",
        "invalid_model": "❌ Неверное имя модели `{}`. Доступные: {}",
        "model_set": "✅ Модель ИИ установлена на `{}`.",
        "no_args_ask": "❓ Укажите вопрос. Использование: `.ask <запрос>`",
        "thinking": "🧠 Думаю с помощью `{}`...",
        "result": "❓ Вопрос:\n{}\n\n💡 Ответ ({}):\n{}",
        "missing_dep": "❌ **Ошибка:** Отсутствует зависимость. Установите необходимые пакеты (`pip install -U g4f`).",
        "request_error": "❌ **Ошибка:** Не удалось получить ответ от `{}`. ({})",
        "unexpected_error": "❌ **Ошибка:** Произошла непредвиденная ошибка при обращении к `{}`. Ошибка: {}",
        "_cmd_doc_ai": "<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        "_cmd_doc_ask": "<запрос> - Задать вопрос выбранной модели ИИ"
    }

    async def client_ready(self, client, db):
        self.db = db
        self._client = g4f.Client()
        self._tg = client
        self._default_model = "gemini-2.0-flash"
        self._available_models = {
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-v3",
            "claude": "claude-3.7-sonnet",
        }
        self.db.setdefault("g4f_model", self._default_model)
    
    async def is_premium_user(self, user_id):
        """Check if user has Telegram Premium"""
        try:
            user = await self._tg.get_entity(user_id)
            return isinstance(user, UserPremium) or hasattr(user, 'premium') and user.premium
        except Exception:
            return False
    
    def format_message_with_animated_emojis(self, message_text, is_premium):
        """Replace standard emojis with animated ones if user is premium"""
        if not is_premium:
            return message_text
            
        # Hardcoded animated emoji IDs - TO BE REPLACED WITH ACTUAL IDs
        animated_emojis = {
            "❓": "<emoji id=5319226943516725959>❓</emoji>",  # Question mark
            "🧠": "<emoji id=5449876550126152994>🧠</emoji>",  # Brain
            "💡": "<emoji id=5451907751829582151>💡</emoji>",  # Light bulb
            "❌": "<emoji id=5465665476971471368>❌</emoji>",  # Error cross
            "✅": "<emoji id=5427009714745517609>✅</emoji>",  # Success checkmark
        }
        
        for standard, animated in animated_emojis.items():
            if standard in message_text:
                message_text = message_text.replace(standard, animated)
                
        return message_text
            
    async def get_formatted_string(self, key, message, *args, **kwargs):
        """Get string with appropriate formatting based on user's premium status"""
        try:
            is_premium = False
            if hasattr(message, 'sender_id') and message.sender_id:
                is_premium = await self.is_premium_user(message.sender_id)
        except Exception:
            logger.debug("Failed to check premium status", exc_info=True)
            is_premium = False
            
        text = self.strings(key).format(*args, **kwargs)
        return self.format_message_with_animated_emojis(text, is_premium)

    @loader.command(
        ru_doc="<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        en_doc="<model_alias> - Set the AI model (gemini, deepseek, claude)",
        aliases=["setmodel"],
    )
    async def ai(self, message: Message):
        """<model_alias> - Set the AI model (gemini, deepseek, claude)"""
        args = utils.get_args_raw(message)
        available_keys = ", ".join(self._available_models.keys())

        if not args:
            current_model = self.db.get("G4fAskMod", "g4f_model", self._default_model)
            text = await self.get_formatted_string("no_args_ai", message, available_keys, current_model)
            await utils.answer(message, text, parse_mode="html")
            return

        model_alias = args.lower().strip()
        if model_alias not in self._available_models:
            text = await self.get_formatted_string("invalid_model", message, model_alias, available_keys)
            await utils.answer(message, text, parse_mode="html")
            return

        selected_model = self._available_models[model_alias]
        self.db.set("G4fAskMod", "g4f_model", selected_model)
        text = await self.get_formatted_string("model_set", message, selected_model)
        await utils.answer(message, text, parse_mode="html")

    @loader.command(
        ru_doc="<запрос> - Задать вопрос выбранной модели ИИ",
        en_doc="<query> - Ask a question to the configured AI model",
        aliases=["a"],
    )
    async def ask(self, message: Message):
        """<query> - Ask a question to the configured AI model"""
        prompt = utils.get_args_raw(message)
        if not prompt:
            # Use edit_delete equivalent for temporary messages
            text = await self.get_formatted_string("no_args_ask", message)
            await utils.answer(message, text, parse_mode="html")
            await asyncio.sleep(5)
            await message.delete()
            return

        model = self.db.get("G4fAskMod", "g4f_model", self._default_model)

        text = await self.get_formatted_string("thinking", message, model)
        msg = await utils.answer(message, text, parse_mode="html")
        
        # Ensure msg is a Message object if utils.answer returns it
        if not isinstance(msg, Message):
            msg = message # Fallback to the original message for context

        try:
            # The chat.completions.create method is not async, so don't use await
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content
            text = await self.get_formatted_string("result", message, prompt, model, answer)
            await utils.answer(msg, text, parse_mode="html")

        except ImportError:
            logger.exception("Missing dependency for g4f")
            text = await self.get_formatted_string("missing_dep", message)
            await utils.answer(msg, text, parse_mode="html")
        except Exception as e:
            error_name = type(e).__name__
            if "request" in error_name.lower():
                logger.exception("Request error from g4f")
                text = await self.get_formatted_string("request_error", message, model, str(e))
                await utils.answer(msg, text, parse_mode="html")
            else:
                logger.exception("Failed to get response from AI")
                text = await self.get_formatted_string("unexpected_error", message, model, str(e))
                await utils.answer(msg, text, parse_mode="html") 
