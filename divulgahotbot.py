from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import os

# Aplicar patch para suportar loop reentrante
nest_asyncio.apply()

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7664156068:AAEsh9NV-eYIP7i_Z12z8UsL6K_36cdLTBQ")  # Substitua pelo token ou use variável de ambiente
ADMIN_ID = int(os.getenv("ADMIN_ID", 6835008287))  # Substitua ou use variável de ambiente

# === FUNÇÕES ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Para adicionar seu CANAL ou GRUPO:\n"
        "Adicione o @divulgalistahotbot como ADM, é grátis\n"
        "Após adicionar já estará na lista no automático!"
    )

async def novo_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    membro = update.chat_member
    if membro.new_chat_member.status in ["administrator", "creator"] and membro.old_chat_member.status not in ["administrator", "creator"]:
        canal_nome = membro.chat.title
        db["canais"].add(membro.chat.id)

        try:
            await context.bot.send_message(
                chat_id=membro.from_user.id,
                text=f"🎉 Caro Administrador, Seu Canal ({canal_nome}) foi APROVADO em nossa lista!! 🎉\n\n"
                     "Não se esqueça de sempre cumprir os requisitos para permanecer na lista!\n\n"
                     "Atenciosamente, Pai Black"
            )
        except:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❗ Não consegui enviar para o ADM de {canal_nome}. Talvez o bot não tenha permissão."
            )

# Ajuste do Pool de Conexões e Timeout
async def main():
    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ajustando o pool de conexões e o timeout
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    await app.bot.delete_webhook(drop_pending_updates=True)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(enviar_relatorio_diario, "cron", hour=0, minute=0, args=[app.bot])
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verificar", comando_verificar))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("visualizacao"), simular_view))
    app.add_handler(ChatMemberHandler(novo_admin, ChatMemberHandler.CHAT_MEMBER))

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.get_running_loop().create_task(main())
    except RuntimeError:
        asyncio.run(main())
