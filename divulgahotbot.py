import logging
import asyncio
import os
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from tinydb import TinyDB, Query

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
db = TinyDB('canais.json')
canais = db.table('canais')

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome_usuario = update.effective_user.first_name
    msg = f"""👋 E "{nome_usuario}"! Bem vindo ao nosso bot de parcerias automáticas

⭐️ COMO FUNCIONA:
Sempre que postarmos links no seu grupos também postaremos o seu link em outros grupos

🤝 PARCERIA JUSTA!
Mantenha cada lista por pelo menos ⏰ 24 horas no seu grupo, caso contrário seu link perderá visibilidade

🟢 REQUISITOS:
-O histórico de conversas precisa estar ativo
-O grupo precisa ou ter mídias ou ser ativo
-O GRUPO É TOTALMENTE GRÁTIS!
-Não pode conter nada ilegal
-Manter cada lista por pelo menos 24 horas

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
    canais.insert({'nome': nome, 'link': link, 'aprovado': True, 'visualizacoes_hoje': 0})
    await update.message.reply_text("🔥 Para adicionar seu CANAL ou GRUPO:\nAdicione o @divulgalistahotbot como ADM, é grátis\napós adicionar já estará na lista no automático!")

    # Envia mensagem ao admin que cadastrou
    if update.message.chat.type in ["group", "supergroup"]:
        admins = await context.bot.get_chat_administrators(update.message.chat_id)
        for adm in admins:
            if not adm.user.is_bot:
                try:
                    await context.bot.send_message(
                        chat_id=adm.user.id,
                        text=f"""🎉 Caro Administrador, Seu Canal ({nome}) foi APROVADO em nossa lista!! 🎉\n\nNão se esqueça de sempre cumprir os requisitos para permanecer na lista!\n\nAtenciosamente, Pai Black"""
                    )
                except:
                    continue

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
            f"""📥 {item['nome']}\n🔗 {item['link']}""",
            reply_markup=keyboard
        )

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

async def enviar_relatorio_diario():
    while True:
        agora = datetime.now()
        proxima_execucao = datetime.combine(agora.date(), time(0, 0))
        if agora >= proxima_execucao:
            proxima_execucao += timedelta(days=1)
        tempo_espera = (proxima_execucao - agora).total_seconds()
        await asyncio.sleep(tempo_espera)

        canais_aprovados = canais.search(Query().aprovado == True)
        total_canais = len(canais_aprovados)
        total_visualizacoes = sum([canal.get("visualizacoes_hoje", 0) for canal in canais_aprovados])
        data_hoje = datetime.now().strftime('%d/%m/%Y')

        msg = f"""📈 *Relatório Diário – {data_hoje}*

Total de visualizações nas listas hoje: {total_visualizacoes:,} 👀
Total de canais participantes: {total_canais}

Continue ativo para manter sua visibilidade no topo, andes com grandes, abraços Tio King! 🚀"""

        await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")

        for canal in canais_aprovados:
            canais.update({"visualizacoes_hoje": 0}, doc_ids=[canal.doc_id])

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cadastrar", cadastrar))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("adminpainel", adminpainel))
    app.add_handler(CallbackQueryHandler(button, pattern="^page_"))
    app.add_handler(CallbackQueryHandler(aprovar_rejeitar, pattern="^(aprovar|rejeitar)_"))

    asyncio.create_task(enviar_relatorio_diario())

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
