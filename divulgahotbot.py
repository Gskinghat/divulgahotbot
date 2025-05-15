
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from tinydb import TinyDB, Query

# Setup
TOKEN = "7664156068:AAEsh9NV-eYIP7i_Z12z8UsL6K_36cdLTBQ"
ADMIN_ID = 6835008287
db = TinyDB('canais.json')
canais = db.table('canais')

logging.basicConfig(level=logging.INFO)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 Bem-vindo ao *DivulgaHotBot!*\n"
        "📢 Aqui você encontra canais e grupos para divulgação de conteúdo adulto, SEO e marketing.\n\n"
        "🔥 Para adicionar seu CANAL ou GRUPO:\n"
        "Use o comando /cadastrar - é grátis e automático!\n\n"
        "⚠️ Regras básicas:\n"
        "- Voltado a conteúdo +18\n"
        "- Descrição clara e ativa\n\n"
        "📊 Lista de Canais e Grupos disponíveis:\n"
        "👉 Use /lista para acessar agora!"
    )
    await update.message.reply_text(msg)

# /cadastrar nome link
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

    canais.insert({'nome': nome, 'link': link, 'aprovado': False})
    await update.message.reply_text("✅ Canal enviado para análise e aprovação!")

# /lista paginada
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

# Paginação
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("page_"):
        page = int(query.data.split("_")[1])
        context.args = [str(page)]
        update.message = query.message
        await lista(update, context)

# /adminpainel
async def adminpainel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Acesso negado.")
        return

    pendentes = canais.search(Query().aprovado == False)
    if not pendentes:
        await update.message.reply_text("✅ Nenhum canal pendente.")
        return

    for item in pendentes:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{item.doc_id}"),
             InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{item.doc_id}")]
        ])
       await update.message.reply_text(
    f"📥 {item['nome']}\n🔗 {item['link']}",
    reply_markup=keyboard
)

# Aprovar ou rejeitar
async def aprovar_rejeitar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, doc_id = query.data.split("_")
    doc_id = int(doc_id)

    if action == "aprovar":
        canais.update({'aprovado': True}, doc_ids=[doc_id])
        await query.edit_message_text("✅ Canal aprovado!")
    elif action == "rejeitar":
        canais.remove(doc_ids=[doc_id])
        await query.edit_message_text("❌ Canal rejeitado e removido.")

# Main
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cadastrar", cadastrar))
app.add_handler(CommandHandler("lista", lista))
app.add_handler(CommandHandler("adminpainel", adminpainel))
app.add_handler(CallbackQueryHandler(button, pattern="^page_"))
app.add_handler(CallbackQueryHandler(aprovar_rejeitar, pattern="^(aprovar|rejeitar)_"))

if __name__ == "__main__":
    app.run_polling()
