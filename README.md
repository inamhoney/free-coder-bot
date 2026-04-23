# Free Coder Bot 🤖⚡

Telegram coding assistant powered by **NVIDIA NIM (Kimi K2)** — completely free, runs 24/7 on Railway.

## Deploy to Railway (5 minutes)

### Step 1: Fork or upload this folder to GitHub
Push the contents of this folder to a new GitHub repo.

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repo
4. Railway auto-detects Python and sets up the build

### Step 3: Add Environment Variables
In Railway dashboard → your project → **Variables** tab, add:

| Variable | Value |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `NVIDIA_NIM_API_KEY` | Your key from build.nvidia.com/settings/api-keys |

### Step 4: Deploy
Click **Deploy** — it starts in ~2 minutes. Your bot is now live 24/7!

## Features
- 🧠 **Kimi K2 Thinking** model — best open model for coding
- ⚡ **GLM 4.7** & **Step 3.5 Flash** — fast fallbacks
- 💬 **Conversation memory** per user (session-based)
- 🔄 **/new** to reset conversation
- 🎯 **/model** to switch between models
- 📦 **40 req/min free** on NVIDIA NIM

## Commands
- `/start` — Welcome + reset session
- `/new` — Clear conversation history
- `/model` — Switch AI model
- `/help` — Help message

## Cost
**Zero.** NVIDIA NIM gives 40 free requests/minute. Railway has a free tier.
