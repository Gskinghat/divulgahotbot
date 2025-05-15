import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, ChatMemberHandler, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === CONFIG ===
BOT_TOKEN = "SEU_TOKEN_AQUI"  # Substitua pelo seu token
ADMIN_ID = 6835008287  # Seu ID Telegram

# Simulando base de dados temporária
db = {
    "views": 0,
    "canais": set(),
}

# === FUNÇÕES ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Para adicionar seu CANAL ou GRUPO:\nAdicione o @divulgalistahotbot como ADM, é grátis\nApós adicionar já estará na lista no automático!"
    )

async def novo_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    membro = update.chat_member
    if (
        membro.new_chat_member.status in ["administrator", "creator"]
        and membro.old_chat_member.status not in ["administrator", "creator"]
    ):
        canal_nome = membro.chat.title
        db["canais"].add(membro.chat.id)
        try:
            await context.bot.send_message(
                chat_id=membro.from_user.id,
                text=f"🎉 Caro Administrador, Seu Canal ({canal_nome}) foi APROVADO em nossa lista!! 🎉\n\nNão se esqueça de sempre cumprir os requisitos para permanecer na lista!\n\nAtenciosamente, Pai Black"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❗ Não consegui enviar para o ADM de {canal_nome}. Talvez o bot não tenha permissão."
            )

async def simular_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db["views"] += 1
    await update.message.reply_text("Visualização simulada!")

async def enviar_relatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime("%d/%m/%Y")
    total_views = db["views"]
    total_canais = len(db["canais"])

    texto = (
        f"📈 Relatório Diário – {hoje}\n\n"
        f"Total de visualizações nas listas hoje: {total_views:,} 👀\n"
        f"Total de canais participantes: {total_canais}\n\n"
        "Continue ativo para manter sua visibilidade no topo, ande com grandes, abraços Tio King! 🚀"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=texto)
    db["views"] = 0  # Resetar views

# === EXECUÇÃO ===

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("visualizacao"), simular_view))
    app.add_handler(ChatMemberHandler(novo_admin, ChatMemberHandler.CHAT_MEMBER))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(enviar_relatorio_diario, "cron", hour=0, minute=0, args=[app.bot])
    scheduler.start()

    print("Bot rodando com polling e agendamento diário!")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
