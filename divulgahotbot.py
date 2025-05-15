import logging
import asyncio
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler,
                          ContextTypes, ChatMemberHandler)
from tinydb import TinyDB, Query

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BACKUP_CHANNEL_ID = os.getenv("BACKUP_CHANNEL_ID")  # Opcional

db = TinyDB('canais.json')
canais = db.table('canais')

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first = update.effective_user.first_name
    msg = f"""👋 E "{user_first}"! Bem vindo ao nosso bot de parcerias automáticas

⭐️ COMO FUNCIONA:
Sempre que postarmos links no seu grupo também postaremos o seu link em outros grupos

🤝 PARCERIA JUSTA!
Mantenha cada lista por pelo menos ⏰ 24 horas no seu grupo, caso contrário seu link perderá visibilidade

🟢 REQUISITOS:
- O histórico de conversas precisa estar ativo
- O grupo precisa ou ter mídias ou ser ativo
- O GRUPO É TOTALMENTE GRÁTIS!
- Não pode conter nada ilegal
- Manter cada lista por pelo menos 24 horas

Clique em \"🟢 Adicionar Bot\" para participar"""
    await update.message.reply_text(msg)

async def cadastrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Use assim: /cadastrar nome @link ou https://t.me/link")
        return
    nome = args[0]
    link = args[1]
    if not link.startswith("@") and "t.me" not in link:
        await update.message.reply_text("❌ Link inválido. Use @canal ou https://t.me/...")
        return
    canais.insert({'nome': nome, 'link': link, 'aprovado': True})
    await update.message.reply_text("✅ Canal cadastrado com sucesso e já está na lista!")

async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(context.args[0]) if context.args else 0
    items = canais.search(Query().aprovado == True)
    items_per_page = 5
    start = page * items_per_page
    end = start + items_per_page
    paginated = items[start:end]
    if not paginated:
        await update.message.reply_text("⚠️ Nenhum canal aprovado encontrado.")
        return
    text = "\n".join([f"🔗 {item['nome']}: {item['link']}" for item in paginated])
    buttons = []
    if start > 0:
        buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"page_{page-1}"))
    if end < len(items):
        buttons.append(InlineKeyboardButton("➡️ Próxima", callback_data=f"page_{page+1}"))
    markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await update.message.reply_text(text, reply_markup=markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("page_"):
        page = int(query.data.split("_")[1])
        context.args = [str(page)]
        update.message = query.message
        await lista(update, context)

async def novo_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_status = update.my_chat_member.new_chat_member.status
    bot_id = context.bot.id

    if new_status == "administrator" and update.my_chat_member.new_chat_member.user.id == bot_id:
        chat = update.effective_chat
        user = update.effective_user

        nome = chat.title or "Grupo sem nome"
        link = f"https://t.me/{chat.username}" if chat.username else "Sem @link"

        if not canais.search((Query().link == link) | (Query().nome == nome)):
            canais.insert({'nome': nome, 'link': link, 'aprovado': True})

        mensagem = f"""🎉 *Caro Administrador*, seu canal *{nome}* foi **APROVADO** em nossa lista! 🎉\n\nNão se esqueça de sempre cumprir os requisitos para permanecer na lista!\n\nAtenciosamente,\n*Pai Black* 🕶️"""
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=mensagem,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.warning(f"[ERRO] Não consegui enviar msg privada para {user.id} — {user.username or 'sem username'} — Erro: {e}")
            if BACKUP_CHANNEL_ID:
                try:
                    await context.bot.send_message(
                        chat_id=BACKUP_CHANNEL_ID,
                        text=f"⚠️ Falha ao notificar ADM `{user.id}` sobre grupo *{nome}*\nErro: `{e}`",
                        parse_mode="Markdown"
                    )
                except:
                    logging.warning("❌ Também falhou ao enviar para canal de backup.")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cadastrar", cadastrar))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CallbackQueryHandler(button, pattern="^page_"))
    app.add_handler(ChatMemberHandler(novo_admin, ChatMemberHandler.MY_CHAT_MEMBER))

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
