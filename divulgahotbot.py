import asyncio
from datetime import datetime
from telegram import Update, Chat
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

# Aplicar patch para suportar loop reentrante
nest_asyncio.apply()

# === CONFIG ===
BOT_TOKEN = "7664156068:AAEsh9NV-eYIP7i_Z12z8UsL6K_36cdLTBQ"
ADMIN_ID = 6835008287

db = {
    "views": 0,
    "canais": set(),
}

# === FUNÇÕES ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Para adicionar seu CANAL ou GRUPO:\n"
        "Adicione o @divulgalistahotbot como ADM, é grátis\n"
        "Após adicionar já estará na lista no automático!"
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
                text=f"🎉 Seu Canal ({canal_nome}) foi APROVADO na lista!\n\n"
                     "Siga as regras para continuar visível!\n\n"
                     "Atenciosamente, Pai Black"
            )
        except:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"❗ Não consegui notificar o ADM de {canal_nome} ({membro.chat.id})"
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
        f"Total de visualizações: {total_views:,} 👀\n"
        f"Canais participantes: {total_canais}\n\n"
        "Continue ativo para manter visibilidade no topo!\n"
        "Abraços, Tio King 🚀"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=texto)
    db["views"] = 0

async def verificar_canais_existentes(app: Application):
    async for dialog in app.bot.get_updates():
        try:
            chat = dialog.message.chat if dialog.message else None
            if chat and chat.type in ["channel", "supergroup"]:
                member = await app.bot.get_chat_member(chat.id, app.bot.id)
                if member.status in ["administrator", "creator"] and chat.id not in db["canais"]:
                    db["canais"].add(chat.id)
                    await app.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"✅ Bot é admin em: {chat.title} ({chat.id})"
                    )
        except Exception as e:
            print(f"Erro ao verificar canal: {e}")

# === MAIN ===

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    await app.bot.delete_webhook(drop_pending_updates=True)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(enviar_relatorio_diario, "cron", hour=0, minute=0, args=[app.bot])
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("visualizacao"), simular_view))
    app.add_handler(ChatMemberHandler(novo_admin, ChatMemberHandler.CHAT_MEMBER))

    # Verifica canais onde o bot já está como admin
    await verificar_canais_existentes(app)

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling()

# Detectar se o loop já está ativo
if __name__ == "__main__":
    try:
        asyncio.get_running_loop().create_task(main())
    except RuntimeError:
        asyncio.run(main())
