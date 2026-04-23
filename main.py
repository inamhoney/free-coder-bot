"""
Free Coder Bot - Telegram bot powered by NVIDIA NIM (Kimi K2 model)
Deploy on Railway for 24/7 free coding assistant via Telegram.
Zero cost - uses NVIDIA NIM free tier (40 req/min)
"""

import os
import re
import json
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
    "kimi":  {"id": "moonshotai/kimi-k2-thinking", "label": "Kimi K2 Thinking 🧠"},
    "glm":   {"id": "z-ai/glm4.7",                 "label": "GLM 4.7 ⚡"},
    "step":  {"id": "stepfun-ai/step-3.5-flash",   "label": "Step 3.5 Flash 🚀"},
}
DEFAULT_MODEL = "kimi"

user_sessions: dict[int, list] = {}

SYSTEM_PROMPT = """You are an expert full-stack coding assistant. You build complete, production-ready code.

When asked to build a website/app/tool:
1. Output COMPLETE, ready-to-run HTML/CSS/JS in a single file
2. Use Tailwind CSS via CDN for styling — always beautiful and modern
3. Make it visually polished — gradients, shadows, hover effects, animations
4. Include ALL functionality — no TODOs, no placeholders
5. For React apps, use CDN-based React + Babel (no build step)

When answering code questions:
- Be concise but complete
- Show working examples
- Briefly explain after the code

Always wrap code in proper markdown code blocks with language tags.
Default: build something beautiful and fully functional immediately."""


def extract_content(message: dict) -> str:
    """Extract text from NVIDIA NIM response, handling thinking models."""
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""

    # Kimi K2 puts final answer in reasoning_content when content is null
    raw = content if content else reasoning

    # Strip <think>...</think> blocks
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
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

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{NVIDIA_NIM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"NVIDIA NIM error {resp.status}: {error_text}")
                raise Exception(f"API error {resp.status}: {error_text[:300]}")

            data = await resp.json()
            msg = data["choices"][0]["message"]
            return extract_content(msg)


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    clear_session(user.id)
    keyboard = [
        [InlineKeyboardButton("🌐 Build a Website", callback_data="ex_website")],
        [InlineKeyboardButton("⚛️ React App", callback_data="ex_react")],
        [InlineKeyboardButton("🐛 Fix My Code", callback_data="ex_fix")],
    ]
    await update.message.reply_text(
        f"⚡ *Free Coder Bot* — Kimi K2 via NVIDIA NIM\n\n"
        f"Hey {user.first_name}! I'm your free coding assistant. Zero cost, 24/7.\n\n"
        f"*Try:*\n"
        f"• Build me a landing page for a gym\n"
        f"• Create a todo app with dark mode\n"
        f"• Make a SaaS pricing page\n"
        f"• Fix this bug: [paste your code]\n\n"
        f"Just type anything 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Commands:*\n\n"
        "/start — Welcome & reset session\n"
        "/new — Clear conversation\n"
        "/model — Switch AI model\n"
        "/help — This message\n\n"
        "*Models available (all free):*\n"
        "🧠 Kimi K2 — best for coding\n"
        "⚡ GLM 4.7 — fast & capable\n"
        "🚀 Step 3.5 Flash — ultrafast\n\n"
        "*Rate limit:* 40 req/min (NVIDIA NIM free tier)",
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
        "Choose your AI model (all free on NVIDIA NIM):",
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
            "ex_website": "Build me a beautiful landing page for a SaaS product called 'FlowAI' that automates workflows. Include hero, features, pricing, and a CTA button.",
            "ex_react":   "Create a React todo app with dark mode, add/delete/complete tasks, and local storage — all in a single HTML file using CDN React.",
            "ex_fix":     "Fix this Python bug and explain what went wrong:\n\n```python\ndef average(nums):\n    return sum(nums) / len(nums)\n\nprint(average([]))\n```",
        }
        prompt = examples.get(data, "Build something cool!")
        await query.edit_message_text(f"Got it! Building now... ⚡")
        await process_message(user_id, prompt, query.message, context)


async def process_message(user_id: int, text: str, message, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(user_id)
    session.append({"role": "user", "content": text})
    model_key = context.user_data.get("model", DEFAULT_MODEL)

    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
        response = await call_nvidia_nim(session, model_key)
        session.append({"role": "assistant", "content": response})

        chunks = split_message(response)
        for i, chunk in enumerate(chunks):
            try:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                # Fallback: send without markdown if formatting fails
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=chunk,
                )

    except Exception as e:
        err = str(e)
        logger.error(f"Error for user {user_id}: {err}")
        if "429" in err or "rate" in err.lower():
            await context.bot.send_message(
                chat_id=message.chat_id,
                text="⏳ Rate limit hit (40 req/min free tier). Wait a sec and try again!"
            )
        elif "401" in err:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text="🔑 NVIDIA NIM API key error. Check your key."
            )
        else:
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"❌ Error: {err[:200]}\n\nTry /new to reset."
            )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(
        update.effective_user.id,
        update.message.text,
        update.message,
        context,
    )


def main():
    logger.info("🚀 Starting Free Coder Bot (NVIDIA NIM / Kimi K2)...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Bot is live!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
