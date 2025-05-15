import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    ChatMemberHandler, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === CONFIG ===
BOT_TOKEN = "SEU_TOKEN_AQUI"  # Substitua pelo seu token real
ADMIN_ID = 6835008287  # Seu ID do Telegram

# === BASE DE DADOS SIMPLES EM MEMÓRIA ===
db = {
    "views": 0,
    "canais": set(),
}

# === FUNÇÕES PRINCIPAIS ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Para adicionar seu CANAL ou GRUPO:\n"
        "Adicione o @divulgalistahotbot como ADM, é grátis.\n"
        "Após adicionar já estará na lista no automático!"
    )

async def novo_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    membro = update.chat_member
    if (
        membro.new_chat_member.status in ["administrator", "creator"] and
        membro.old_chat_member.status not in ["administrator", "creator"]
    ):
        canal_nome = membro.chat.title
        db["canais"].add(membro.chat.id)

        try:
            await context.bot.send_message(
                chat_id=membro.from_user.id,
                text=(
                    f"🎉 Caro Administrador, seu canal ({canal_nome}) foi APROVADO em nossa lista!! 🎉\n\n"
                    "Não se esqueça de sempre cumprir os requisitos para permanecer na lista!\n\n"
                    "Atenciosamente, Pai Black"
                )
            )
        except:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"❗ Não consegui enviar para o ADM de {canal_nome}. "
                    "Talvez o bot não tenha permissão ou o ADM não iniciou o bot no privado."
                )
            )

async def simular_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db["views"] += 1
    await update.message.reply_text("✅ Visualização simulada registrada!")

async def enviar_relatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime("%d/%m/%Y")
    total_views = db["views"]
    total_canais = len(db["canais"])
    
    texto = (
        f"📈 Relatório Diário – {hoje}\n\n"
        f"👀 Total de visualizações nas listas: {total_views:,}\n"
        f"📡 Total de canais participantes: {total_canais}\n\n"
        "Continue ativo para manter sua visibilidade no topo. Abraços, Tio King! 🚀"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=texto)
    db["views"] = 0  # Zera o contador de views

# === EXECUÇÃO PRINCIPAL ===

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Remove o webhook para evitar
