# meta developer: @mlwdev
# scope: hikka_only

import logging
import g4f
import asyncio
import functools
import html

from .. import loader, utils
from telethon.tl.types import Message, User

logger = logging.getLogger(__name__)

STATIC_EMOJIS = {
    "q": "❓",
    "brain": "🧠",
    "bulb": "💡",
    "cross": "❌",
    "tick": "✅",
}

ANIMATED_EMOJIS = {
    "q": "<emoji document_id=5319226943516725959>😘</emoji>",
    "brain": "<emoji document_id=5449876550126152994>😔</emoji>",
    "bulb": "<emoji document_id=5451907751829582151>🤔</emoji>",
    "cross": "<emoji document_id=5465665476971471368>❌</emoji>",
    "tick": "<emoji document_id=5427009714745517609>✅</emoji>",
}

@loader.tds
class G4fAskMod(loader.Module):
    """Модуль для взаимодействия с ИИ моделями через g4f"""
    strings = {
        "name": "G4fAsk",
        "no_args_ai": "{q} <b>Usage:</b> <code>.ai <model_alias></code>\n<b>Available:</b> <code>{available}</code>\n<b>Current:</b> <code>{current}</code>",
        "invalid_model": "{cross} <b>Invalid model alias</b> <code>{alias}</code>. Available: {available}",
        "model_set": "{tick} <b>AI model set to</b> <code>{model}</code>.",
        "no_args_ask": "{q} <b>Please provide a question.</b> Usage: <code>.ask <query></code>",
        "thinking": "{brain} <b>Thinking</b> with <code>{model}</code>...",
        "result": "<b>{q} Question:</b>\n{prompt}\n\n<b>{bulb} Answer ({model}):</b>\n{answer}",
        "missing_dep": "{cross} <b>Error:</b> Missing dependency. Please install required packages (<code>pip install -U g4f</code>).",
        "request_error": "{cross} <b>Error:</b> Failed to get response from <code>{model}</code>. ({error})",
        "unexpected_error": "{cross} <b>Error:</b> An unexpected error occurred while contacting <code>{model}</code>. Error: {error}",
    }
    strings_ru = {
        "_cls_doc": "Модуль для взаимодействия с ИИ моделями через g4f",
        "no_args_ai": "{q} <b>Использование:</b> <code>.ai <модель></code>\n<b>Доступные:</b> <code>{available}</code>\n<b>Текущая:</b> <code>{current}</code>",
        "invalid_model": "{cross} <b>Неверное имя модели</b> <code>{alias}</code>. Доступные: {available}",
        "model_set": "{tick} <b>Модель ИИ установлена на</b> <code>{model}</code>.",
        "no_args_ask": "{q} <b>Укажите вопрос.</b> Использование: <code>.ask <запрос></code>",
        "thinking": "{brain} <b>Думаю</b> с помощью <code>{model}</code>...",
        "result": "<b>{q} Вопрос:</b>\n{prompt}\n\n<b>{bulb} Ответ ({model}):</b>\n{answer}",
        "missing_dep": "{cross} <b>Ошибка:</b> Отсутствует зависимость. Установите необходимые пакеты (<code>pip install -U g4f</code>).",
        "request_error": "{cross} <b>Ошибка:</b> Не удалось получить ответ от <code>{model}</code>. ({error})",
        "unexpected_error": "{cross} <b>Ошибка:</b> Произошла непредвиденная ошибка при обращении к <code>{model}</code>. Ошибка: {error}",
        "_cmd_doc_ai": "<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        "_cmd_doc_ask": "<запрос> - Задать вопрос выбранной модели ИИ"
    }

    def __init__(self):
        self.config = loader.ModuleConfig()

    async def client_ready(self, client, db):
        self.db = db
        try:
            import g4f
            self._client = g4f.Client()
        except ImportError:
            logger.critical("g4f library not found. Install it using 'pip install -U g4f'")
            self._client = None

        self._default_model = "gemini-2.0-flash"
        self._available_models = {
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-v3",
            "claude": "claude-3.7-sonnet",
        }
        if "G4fAskMod" not in self.db:
            self.db["G4fAskMod"] = {}
        if "g4f_model" not in self.db["G4fAskMod"]:
             self.db.set("G4fAskMod", "g4f_model", self._default_model)


    def _get_emojis(self, user: User) -> dict:
        return ANIMATED_EMOJIS if getattr(user, 'premium', False) else STATIC_EMOJIS

    async def _answer(self, message: Message, text: str, **kwargs):
        """Helper to answer with HTML parse mode."""
        # Ensure emojis are not escaped by html.escape later
        emojis = kwargs.get("emojis", {})
        formatted_text = text.format(**kwargs, **emojis)

        # Escape only specific parts if needed, otherwise send as is
        # For simplicity now, send as is assuming strings are safe HTML
        await utils.answer(message, formatted_text, parse_mode='html')

    async def _answer_result(self, message: Message, text: str, prompt:str, answer:str, **kwargs):
        """Helper for the result message, escaping prompt and answer."""
        emojis = kwargs.get("emojis", {})
        # Escape user prompt and AI answer to prevent HTML injection
        safe_prompt = html.escape(prompt)
        safe_answer = html.escape(answer) # Escape AI answer by default
        # If you trust AI to generate safe HTML/Markdown and want to render it:
        # safe_answer = answer # Uncomment this line
        # You might need more sophisticated sanitization then.

        formatted_text = text.format(
            prompt=safe_prompt,
            answer=safe_answer, # Use the escaped version
            **kwargs,
            **emojis
        )
        await utils.answer(message, formatted_text, parse_mode='html')


    @loader.command(
        ru_doc="<модель> - Установить модель ИИ (gemini, deepseek, claude)",
        en_doc="<model_alias> - Set the AI model (gemini, deepseek, claude)",
        aliases=["setmodel"],
    )
    async def ai(self, message: Message):
        sender = await message.get_sender()
        emojis = self._get_emojis(sender)

        if not self._client:
             await self._answer(message, self.strings("missing_dep"), emojis=STATIC_EMOJIS)
             return

        args = utils.get_args_raw(message)
        available_keys = ", ".join(f"<code>{key}</code>" for key in self._available_models.keys()) # Use code tags for keys

        if not args:
            current_model = self.db.get("G4fAskMod", "g4f_model", self._default_model)
            await self._answer(
                message,
                self.strings("no_args_ai"),
                available=available_keys,
                current=f"<code>{current_model}</code>",
                emojis=emojis
            )
            return

        model_alias = args.lower().strip()
        if model_alias not in self._available_models:
            await self._answer(
                message,
                self.strings("invalid_model"),
                alias=html.escape(model_alias), # Escape user input
                available=available_keys,
                emojis=emojis
            )
            return

        selected_model = self._available_models[model_alias]
        self.db.set("G4fAskMod", "g4f_model", selected_model)

        await self._answer(
            message,
            self.strings("model_set"),
            model=f"<code>{selected_model}</code>",
            emojis=emojis
        )

    @loader.command(
        ru_doc="<запрос> - Задать вопрос выбранной модели ИИ",
        en_doc="<query> - Ask a question to the configured AI model",
        aliases=["a"],
    )
    async def ask(self, message: Message):
        sender = await message.get_sender()
        emojis = self._get_emojis(sender)

        if not self._client:
             await self._answer(message, self.strings("missing_dep"), emojis=STATIC_EMOJIS)
             return

        prompt = utils.get_args_raw(message)

        if not prompt:
            msg_to_del = await self._answer(
                message,
                self.strings("no_args_ask"),
                emojis=emojis
            )
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

        msg = await self._answer(
            message,
            self.strings("thinking"),
            model=f"<code>{model}</code>",
            emojis=emojis
        )
        if not isinstance(msg, Message):
            msg = message

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

            await self._answer_result(
                msg,
                self.strings("result"),
                prompt=prompt, # Will be escaped by _answer_result
                answer=answer, # Will be escaped by _answer_result
                model=f"<code>{model}</code>",
                emojis=emojis
            )

        except ImportError:
            logger.exception("Missing dependency for g4f")
            await self._answer(msg, self.strings("missing_dep"), emojis=emojis)
        except Exception as e:
            error_name = type(e).__name__
            logger.exception(f"Error during g4f request: {e}")
            error_str = str(e).lower()
            safe_error = html.escape(str(e)) # Escape error message

            if "request" in error_name.lower() or "request" in error_str or "api" in error_str or "network" in error_str or "connection" in error_str or "empty or invalid response" in error_str:
                await self._answer(
                    msg,
                    self.strings("request_error"),
                    model=f"<code>{model}</code>",
                    error=safe_error,
                    emojis=emojis
                )
            else:
                await self._answer(
                    msg,
                    self.strings("unexpected_error"),
                    model=f"<code>{model}</code>",
                    error=safe_error,
                    emojis=emojis
                )
