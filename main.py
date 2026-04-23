"""
Free Coder Bot 1 - @Coding_inam_bot
Telegram coding assistant powered by NVIDIA NIM.
Railway deployment — zero cost, 24/7.
"""

import os
import re
import asyncio
import aiohttp
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
NVIDIA_NIM_API_KEY = os.environ["NVIDIA_NIM_API_KEY"]
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELS = {
    "kimi": {"id": "moonshotai/kimi-k2-thinking",  "label": "Kimi K2 🧠 (deep)"},
    "glm":  {"id": "z-ai/glm4.7",                  "label": "GLM 4.7 ⚡ (fast)"},
    "step": {"id": "stepfun-ai/step-3.5-flash",     "label": "Step 3.5 🚀 (fastest)"},
}
DEFAULT_MODEL = "glm"   # GLM is fast AND reliable for coding

user_sessions: dict[int, list] = {}

SYSTEM_PROMPT = """You are an expert full-stack coding assistant. You write complete, production-ready code.

Rules:
- Always wrap code in markdown code blocks with the correct language tag
- Be concise but complete — no truncated code, no TODOs
- For bug fixes: show the fixed code + one-line explanation
- For builds: output a single complete HTML file using Tailwind CDN
- Keep responses under 3000 characters when possible"""


def extract_content(message: dict) -> str:
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    raw = content if content else reasoning
    # Strip <think>...</think> blocks
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.DOTALL).strip()
    # If nothing left after stripping (still generating thinking), return raw
    return cleaned if cleaned else raw.strip()


async def call_nvidia_nim(messages: list, model_key: str = DEFAULT_MODEL) -> str:
    model_id = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["id"]
    headers = {
        "Authorization": f"Bearer {NVIDIA_NIM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 4096,
        "stream": False,
    }
    last_err = None
    for attempt in range(3):
        try:
            if attempt > 0:
                await asyncio.sleep(4 * attempt)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{NVIDIA_NIM_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as resp:
                    if resp.status in (502, 503, 504):
                        last_err = Exception(f"NVIDIA server busy ({resp.status}), retrying...")
                        logger.warning(f"Attempt {attempt+1}: NVIDIA {resp.status}, retrying...")
                        continue
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"NVIDIA API error {resp.status}: {error_text[:300]}")
                    data = await resp.json()
                    msg = data["choices"][0]["message"]
                    result = extract_content(msg)
                    if not result:
                        raise Exception("Model returned empty — try /model glm or retry")
                    return result
        except asyncio.TimeoutError:
            last_err = Exception("Request timed out — try /model step for fastest responses.")
            continue
        except aiohttp.ClientError as e:
            last_err = Exception(f"Network error: {str(e)}")
            continue
    raise last_err or Exception("Failed after 3 attempts")



def get_session(user_id: int) -> list:
    if user_id not in user_sessions:
        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return user_sessions[user_id]


def clear_session(user_id: int):
    user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]


def split_message(text: str, max_length: int = 4000) -> list[str]:
    if len(text) <= max_length:
        return [text]
    chunks = []
    while len(text) > max_length:
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


async def keep_typing(bot, chat_id: int, stop_event: asyncio.Event):
    """Send typing action every 4 seconds until stopped."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.sleep(4)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clear_session(user.id)
    keyboard = [
        [InlineKeyboardButton("🌐 Build a Website", callback_data="ex_website")],
        [InlineKeyboardButton("⚛️ React App",        callback_data="ex_react")],
        [InlineKeyboardButton("🐛 Fix My Code",      callback_data="ex_fix")],
    ]
    await update.message.reply_text(
        f"⚡ *Free Coder Bot* — NVIDIA NIM\n\n"
        f"Hey {user.first_name}! Zero cost coding assistant, 24/7.\n\n"
        f"*Try:*\n"
        f"• Build me a landing page for a gym\n"
        f"• Create a todo app with dark mode\n"
        f"• Fix this bug: [paste code]\n\n"
        f"Just type 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data.get("model", DEFAULT_MODEL)
    await update.message.reply_text(
        f"🤖 *Commands:*\n\n"
        f"/start — Reset session\n"
        f"/new — Clear conversation\n"
        f"/model — Switch AI model\n"
        f"/help — This message\n\n"
        f"*Models (all free via NVIDIA NIM):*\n"
        f"🧠 kimi — Kimi K2 (best quality, slow)\n"
        f"⚡ glm  — GLM 4.7 (fast + smart) ← default\n"
        f"🚀 step — Step 3.5 Flash (ultrafast)\n\n"
        f"Current: *{MODELS[current]['label']}*",
        parse_mode=ParseMode.MARKDOWN,
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_session(update.effective_user.id)
    await update.message.reply_text("🔄 Session cleared! What do you want to build?")


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data.get("model", DEFAULT_MODEL)
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if current == k else ''}{v['label']}",
            callback_data=f"model_{k}"
        )]
        for k, v in MODELS.items()
    ]
    await update.message.reply_text(
        "Choose AI model (all free on NVIDIA NIM):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("model_"):
        key = data[6:]
        context.user_data["model"] = key
        label = MODELS[key]["label"]
        await query.edit_message_text(
            f"✅ Switched to *{label}*\n\nWhat do you want to build?",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data.startswith("ex_"):
        examples = {
            "ex_website": "Build a beautiful landing page for a SaaS product called 'FlowAI'. Single HTML file with Tailwind. Include hero, features, pricing, CTA.",
            "ex_react":   "Create a React todo app with dark mode, add/delete/complete tasks, local storage — single HTML file with CDN React.",
            "ex_fix":     "Fix this Python bug:\n\ndef average(nums):\n    return sum(nums) / len(nums)\n\nprint(average([]))",
        }
        prompt = examples.get(data, "Build something cool!")
        await query.edit_message_text(f"⚡ Working on it...")
        await process_message(user_id, prompt, query.message, context)


async def process_message(user_id: int, text: str, message, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(user_id)
    session.append({"role": "user", "content": text})
    model_key = context.user_data.get("model", DEFAULT_MODEL)
    model_label = MODELS[model_key]["label"]

    stop_event = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(context.bot, message.chat_id, stop_event))

    try:
        response = await call_nvidia_nim(session, model_key)
        session.append({"role": "assistant", "content": response})

        stop_event.set()
        await typing_task

        for chunk in split_message(response):
            try:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                await context.bot.send_message(chat_id=message.chat_id, text=chunk)

    except Exception as e:
        stop_event.set()
        await typing_task
        err = str(e) or "Unknown error"
        logger.error(f"Error for user {user_id}: {err}")

        if "429" in err or "rate" in err.lower():
            msg = "⏳ Rate limit hit (40 req/min free tier). Wait a moment and try again!"
        elif "401" in err:
            msg = "🔑 NVIDIA API key error."
        elif "timed out" in err.lower() or "timeout" in err.lower():
            msg = f"⏳ *{model_label}* took too long.\n\nTry `/model step` for the fastest model, then resend."
        elif "empty response" in err.lower():
            msg = "⚠️ Model returned empty. Try again or use `/model glm` for more reliable responses."
        else:
            msg = f"❌ *Error:* {err[:200]}\n\nTry /new to reset or /model to switch models."

        try:
            await context.bot.send_message(
                chat_id=message.chat_id, text=msg, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await context.bot.send_message(chat_id=message.chat_id, text=msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(
        update.effective_user.id,
        update.message.text,
        update.message,
        context,
    )



def main():
    logger.info("🚀 Starting Free Coder Bot 1...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # drop_pending_updates + allowed_updates to avoid conflicts
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    import time
    for i in range(5):
        try:
            main()
            break
        except Exception as e:
            if "Conflict" in str(e):
                logger.warning(f"Conflict on start, waiting 10s... (attempt {i+1})")
                time.sleep(10)
            else:
                raise
