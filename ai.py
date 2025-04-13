# meta developer: @mlwdev
# scope: hikka_only

import logging
import g4f
import asyncio
import functools

from .. import loader, utils
from telethon.tl.types import Message, User

logger = logging.getLogger(__name__)

# --- Constants for Emojis ---
# Static Emojis
STATIC_EMOJIS = {
    "q": "❓",
    "brain": "🧠",
    "bulb": "💡",
    "cross": "❌",
    "tick": "✅",
}

# Animated Emojis (for Premium users)
ANIMATED_EMOJIS = {
    "q": "<emoji document_id=5319226943516725959>😘</emoji>",
    "brain": "<emoji document_id=5449876550126152994>😔</emoji>",
    "bulb": "<emoji document_id=5451907751829582151>🤔</emoji>",
    "cross": "<emoji document_id=5465665476971471368>❌</emoji>",
    "tick": "<emoji document_id=5427009714745517609>✅</emoji>",
}
# --- End Constants ---

@loader.tds
class G4fAskMod(loader.Module):
    """Модуль для взаимодействия с ИИ моделями через g4f"""
    strings = {
        "name": "G4fAsk",
        # --- Strings using Markdown Bold ---
        "no_args_ai": "{q} **Usage:** `.ai <model_alias>`\n**Available:** `{available}`\n**Current:** `{current}`",
        "invalid_model": "{cross} **Invalid model alias** `{alias}`. Available: {available}",
        "model_set": "{tick} **AI model set to** `{model}`.",
        "no_args_ask": "{q} **Please provide a question.** Usage: `.ask <query>`",
        "thinking": "{brain} **Thinking** with `{model}`...",
        "result": "**{q} Question:**\n{prompt}\n\n**{bulb} Answer ({model}):**\n{answer}",
        "missing_dep": "{cross} **Error:** Missing dependency. Please install required packages (`pip install -U g4f`).",
        "request_error": "{cross} **Error:** Failed to get response from `{model}`. ({error})",
        "unexpected_error": "{cross} **Error:** An unexpected error occurred while contacting `{model}`. Error: {error}",
        # --- End Strings ---
    }
    strings_ru = {
        "_cls_doc": "Модуль для взаимодействия с ИИ моделями через g4f",
        # --- Strings using Markdown Bold ---
        "no_args_ai": "{q} **Использование:** `.ai <модель>`\n**Доступные:** `{available}`\n**Текущая:** `{current}`",
        "invalid_model": "{cross} **Неверное имя модели** `{alias}`. Доступные: {available}",
        "model_set": "{tick} **Модель ИИ установлена на** `{model}`.",
        "no_args_ask": "{q} **Укажите вопрос.** Использование: `.ask <запрос>`",
        "thinking": "{brain} **Думаю** с помощью `{model}`...",
        "result": "**{q} Вопрос:**\n{prompt}\n\n**{bulb} Ответ ({model}):**\n{answer}",
        "missing_dep": "{cross} **Ошибка:** Отсутствует зависимость. Установите необходимые пакеты (`pip install -U g4f`).",
        "request_error": "{cross} **Ошибка:** Не удалось получить ответ от `{model}`. ({error})",
        "unexpected_error": "{cross} **Ошибка:** Произошла непредвиденная ошибка при обращении к `{model}`. Ошибка: {error}",
        # --- End Strings ---
        "_cmd_doc_ai": "<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        "_cmd_doc_ask": "<запрос> - Задать вопрос выбранной модели ИИ"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            # Configuration settings can go here if needed in the future
        )

    async def client_ready(self, client, db):
        self.db = db
        # Ensure g4f is installed before trying to use it
        try:
            import g4f
            self._client = g4f.Client()
        except ImportError:
            logger.critical("g4f library not found. Install it using 'pip install -U g4f'")
            self._client = None # Indicate that the client is not available

        self._default_model = "gemini-2.0-flash"
        self._available_models = {
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-v3",
            "claude": "claude-3.7-sonnet",
        }
        # Initialize DB settings
        if "G4fAskMod" not in self.db:
            self.db["G4fAskMod"] = {}
        if "g4f_model" not in self.db["G4fAskMod"]:
             self.db.set("G4fAskMod", "g4f_model", self._default_model)


    # --- Helper to get emojis based on premium status ---
    def _get_emojis(self, user: User) -> dict:
        """Returns the correct emoji dict based on user's premium status"""
        return ANIMATED_EMOJIS if getattr(user, 'premium', False) else STATIC_EMOJIS
    # --- End Helper ---

    @loader.command(
        ru_doc="<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        en_doc="<model_alias> - Set the AI model (gemini, deepseek, claude)",
        aliases=["setmodel"],
    )
    async def ai(self, message: Message):
        """<model_alias> - Set the AI model (gemini, deepseek, claude)"""
        if not self._client:
             await utils.answer(message, self.strings("missing_dep").format(**STATIC_EMOJIS), parse_mode='md')
             return

        args = utils.get_args_raw(message)
        available_keys = ", ".join(self._available_models.keys())
        sender = await message.get_sender()
        emojis = self._get_emojis(sender)

        if not args:
            current_model = self.db.get("G4fAskMod", "g4f_model", self._default_model)
            await utils.answer(
                message,
                self.strings("no_args_ai").format(
                    available=available_keys,
                    current=current_model,
                    **emojis
                ),
                parse_mode='md' # Explicitly set parse mode
            )
            return

        model_alias = args.lower().strip()
        if model_alias not in self._available_models:
            await utils.answer(
                message,
                self.strings("invalid_model").format(
                    alias=model_alias,
                    available=available_keys,
                    **emojis
                ),
                parse_mode='md' # Explicitly set parse mode
            )
            return

        selected_model = self._available_models[model_alias]
        self.db.set("G4fAskMod", "g4f_model", selected_model)

        await utils.answer(
            message,
            self.strings("model_set").format(
                model=selected_model,
                **emojis
            ),
            parse_mode='md' # Explicitly set parse mode
        )

    @loader.command(
        ru_doc="<запрос> - Задать вопрос выбранной модели ИИ",
        en_doc="<query> - Ask a question to the configured AI model",
        aliases=["a"],
    )
    async def ask(self, message: Message):
        """<query> - Ask a question to the configured AI model"""
        if not self._client:
             await utils.answer(message, self.strings("missing_dep").format(**STATIC_EMOJIS), parse_mode='md')
             return

        prompt = utils.get_args_raw(message)
        sender = await message.get_sender()
        emojis = self._get_emojis(sender)

        if not prompt:
            msg_to_del = await utils.answer(
                message,
                self.strings("no_args_ask").format(**emojis),
                parse_mode='md' # Explicitly set parse mode
            )
            # Shorten delete delay
            await asyncio.sleep(3)
            if isinstance(msg_to_del, Message):
                try:
                    await msg_to_del.delete()
                except Exception: pass
            else:
                try:
                    await message.delete()
                except Exception: pass
            return

        model = self.db.get("G4fAskMod", "g4f_model", self._default_model)

        msg = await utils.answer(
            message,
            self.strings("thinking").format(model=model, **emojis),
            parse_mode='md' # Explicitly set parse mode
        )
        if not isinstance(msg, Message):
            msg = message # Fallback to editing original message

        try:
            func_call = functools.partial(
                self._client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                func_call
            )

            if not response or not response.choices:
                 logger.warning(f"Received empty or invalid response from API for model {model}. Response: {response}")
                 raise Exception("Empty or invalid response from API")

            answer = response.choices[0].message.content
            # Ensure the answer itself doesn't contain markdown conflicting chars if not intended
            # Basic escaping (can be improved if needed)
            # answer = answer.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

            await utils.answer(
                msg,
                self.strings("result").format(
                    prompt=prompt,
                    model=model,
                    answer=answer, # Send potentially markdown-containing answer
                    **emojis
                ),
                parse_mode='md' # Explicitly set parse mode for the result message
            )

        except ImportError: # Should be caught earlier now, but keep for safety
            logger.exception("Missing dependency for g4f")
            await utils.answer(msg, self.strings("missing_dep").format(**emojis), parse_mode='md')
        except Exception as e:
            error_name = type(e).__name__
            logger.exception(f"Error during g4f request: {e}")
            error_str = str(e).lower()
            if "request" in error_name.lower() or "request" in error_str or "api" in error_str or "network" in error_str or "connection" in error_str or "empty or invalid response" in error_str:
                await utils.answer(
                    msg,
                    self.strings("request_error").format(
                        model=model,
                        error=str(e),
                        **emojis
                    ),
                    parse_mode='md' # Explicitly set parse mode
                )
            else:
                await utils.answer(
                    msg,
                    self.strings("unexpected_error").format(
                        model=model,
                        error=str(e),
                        **emojis
                    ),
                    parse_mode='md' # Explicitly set parse mode
                )
