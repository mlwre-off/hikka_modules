# -*- coding: utf-8 -*-

import logging
from typing import TYPE_CHECKING

from g4f.client import Client
from g4f.errors import MissingDependency, RequestError

from hikka.mod import Module
from hikka.utils import edit_delete, edit_msg

if TYPE_CHECKING:
    import hikari

logger = logging.getLogger(__name__)


class G4fAskMod(Module):
    """Hikka module for interacting with AI models via g4f"""

    async def mod_onload(self):
        """Load database configuration"""
        self._client = Client()
        self._default_model = "gemini-2.0-flash"
        self._available_models = {
            "gemini": "gemini-2.0-flash",
            "deepseek": "deepseek-v3",
            "claude": "claude-3.7-sonnet",
        }
        self.db.setdefault("g4f_model", self._default_model)

    @Module.command(
        "ai",
        args_usage="<model_alias>",
        description="Set the AI model to use (gemini, deepseek, claude)",
        aliases=["setmodel"],
    )
    async def set_ai_model(self, msg: "hikari.MessageCreateEvent"):
        """Sets the AI model"""
        args = msg.message.content.split(maxsplit=1)
        if len(args) < 2 or not args[1]:
            current_model = self.db.get("g4f_model", self._default_model)
            model_aliases = ", ".join(self._available_models.keys())
            await edit_msg(
                msg,
                f"""**Usage:** `.ai <model_alias>`
**Available models:** {model_aliases}
**Current model:** `{current_model}`"""
            )
            return

        model_alias = args[1].lower().strip()
        if model_alias not in self._available_models:
            await edit_msg(msg, f"❌ Invalid model alias `{model_alias}`. Available: {', '.join(self._available_models.keys())}")
            return

        selected_model = self._available_models[model_alias]
        self.db["g4f_model"] = selected_model
        await edit_msg(msg, f"✅ AI model set to `{selected_model}`.")


    @Module.command(
        "ask",
        args_usage="<query>",
        description="Ask a question to the configured AI model",
        aliases=["a"],
    )
    async def ask_ai(self, msg: "hikari.MessageCreateEvent"):
        """Asks the AI"""
        query = msg.message.content.split(maxsplit=1)
        if len(query) < 2 or not query[1]:
            await edit_delete(msg, "❓ Please provide a question. Usage: `.ask <query>`", 5)
            return

        prompt = query[1].strip()
        model = self.db.get("g4f_model", self._default_model)

        await edit_msg(msg, f"🧠 Thinking with `{model}`...")

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content
            await edit_msg(msg, f"**❓ Question:**
{prompt}

**💡 Answer ({model}):**
{answer}")

        except MissingDependency as e:
            logger.exception("Missing dependency for g4f")
            await edit_msg(msg, f"❌ **Error:** Missing dependency `{e}`. Please install it.")
        except RequestError as e:
            logger.exception("Request error from g4f")
            await edit_msg(msg, f"❌ **Error:** Failed to get response from `{model}`. ({e})")
        except Exception:
            logger.exception("Failed to get response from AI")
            await edit_msg(msg, f"❌ **Error:** An unexpected error occurred while contacting `{model}`.") 
