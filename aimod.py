# meta developer: @mlwdev
# scope: hikka_only

import logging
import g4f
import asyncio

from .. import loader, utils
from telethon.tl.types import Message

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
        self._default_model = "gemini-2.0-flash"
        self._available_models = {
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-v3",
            "claude": "claude-3.7-sonnet",
        }
        self.db.setdefault("g4f_model", self._default_model)

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
            await utils.answer(
                message, self.strings("no_args_ai").format(available_keys, current_model)
            )
            return

        model_alias = args.lower().strip()
        if model_alias not in self._available_models:
            await utils.answer(
                message, self.strings("invalid_model").format(model_alias, available_keys)
            )
            return

        selected_model = self._available_models[model_alias]
        self.db.set("G4fAskMod", "g4f_model", selected_model)
        await utils.answer(message, self.strings("model_set").format(selected_model))

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
            await utils.answer(message, self.strings("no_args_ask"), parse_mode="markdown")
            await asyncio.sleep(5)
            await message.delete()
            # Attempt to delete the bot's response if possible
            # This part is tricky as utils.answer might not return the message object
            # depending on Hikka version/configuration
            return

        model = self.db.get("G4fAskMod", "g4f_model", self._default_model)

        msg = await utils.answer(message, self.strings("thinking").format(model), parse_mode="markdown")
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
            await utils.answer(msg, self.strings("result").format(prompt, model, answer), parse_mode="markdown")

        except ImportError:
            logger.exception("Missing dependency for g4f")
            await utils.answer(msg, self.strings("missing_dep"), parse_mode="markdown")
        except Exception as e:
            error_name = type(e).__name__
            if "request" in error_name.lower():
                logger.exception("Request error from g4f")
                await utils.answer(msg, self.strings("request_error").format(model, str(e)), parse_mode="markdown")
            else:
                logger.exception("Failed to get response from AI")
                await utils.answer(msg, self.strings("unexpected_error").format(model, str(e)), parse_mode="markdown") 
