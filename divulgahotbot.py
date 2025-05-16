import asyncio
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import os
from shutil import copy

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Aplicar patch para suportar loop reentrante
nest_asyncio.apply()

# === CONFIG ===
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Banco de dados SQLite para persistência
conn = sqlite3.connect('bot_data.db')
cursor = conn.cursor()

# Criando a tabela caso não exista
cursor.execute('''CREATE TABLE IF NOT EXISTS canais (
                    chat_id INTEGER PRIMARY KEY
                )''')
cursor.execute('''CREATE TABLE IF NOT EXISTS views (
                    total_views INTEGER
                )''')
# Inicializa o total de views
cursor.execute("INSERT OR IGNORE INTO views (total_views) VALUES (0)")
conn.commit()

# Funções de persistência
def get_views():
    cursor.execute("SELECT total_views FROM views WHERE rowid = 1")
    return cursor.fetchone()[0]

def update_views(new_views):
    cursor.execute("UPDATE views SET total_views = ? WHERE rowid = 1", (new_views,))
    conn.commit()

def add_canal(chat_id):
    cursor.execute("INSERT OR IGNORE INTO canais (chat_id) VALUES (?)", (chat_id,))
    conn.commit()

def get_canais():
    cursor.execute("SELECT * FROM canais")
    return cursor.fetchall()

# === FUNÇÕES ===

# Função para verificar os canais onde o bot é administrador
async def verificar_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    canais_verificados = []

    for canal in get_canais():  # Lista dos canais cadastrados
        try:
            membro = await bot.get_chat_member(canal[0], bot.id)
            if membro.status in ["administrator", "creator"]:
                canais_verificados.append(canal[0])
        except Exception as e:
            logger.error(f"Erro ao verificar {canal[0]}: {e}")

    texto = f"✅ Bot é administrador em {len(canais_verificados)} canais públicos."
    await update.message.reply_text(texto)

# Função para verificar administradores automaticamente, com fake update e context
async def verificar_admins_auto(bot):
    # Criando um fake de update e context para poder passar para a função verificar_admins
    from telegram import Update
    from telegram.ext import ContextTypes

    # Criando um fake de 'update' e 'context'
    fake_update = Update(update_id=0, message=None)  # Usar um objeto de mensagem fake
    fake_context = ContextTypes.DEFAULT_TYPE(bot=bot)

    # Chamando a função de verificar admins
    await verificar_admins(fake_update, fake_context)

# Função para enviar mensagem periodicamente
async def enviar_mensagem_periodica(bot, horario):
    mensagem = f"⏰ Hora de se atualizar! A mensagem programada para {horario} foi enviada!"
    # Enviar para o admin ou um grupo específico, aqui estou enviando para o ADMIN_ID
    await bot.send_message(chat_id=ADMIN_ID, text=mensagem)

# Função para enviar o relatório diário
async def enviar_relatorio_diario(context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime("%d/%m/%Y")
    total_views = get_views()
    total_canais = len(get_canais())

    texto = (
        f"📈 Relatório Diário – {hoje}\n\n"
        f"Total de visualizações nas listas hoje: {total_views:,} 👀\n"
        f"Total de canais participantes: {total_canais}\n\n"
        "Continue ativo para manter sua visibilidade no topo, ande com grandes, abraços Tio King! 🚀"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=texto)
        update_views(0)  # Resetando o contador de visualizações
    except Exception as e:
        logger.error(f"Erro ao enviar relatório diário: {e}")

# Função para enviar o relatório semanal
async def enviar_relatorio_semanal(context: ContextTypes.DEFAULT_TYPE):
    hoje = datetime.now().strftime("%d/%m/%Y")
    total_views = get_views()
    total_canais = len(get_canais())

    texto = (
        f"🏆 Relatório Semanal – {hoje}\n\n"
        f"Total de visualizações nas listas esta semana: {total_views:,} 👀\n"
        f"Total de canais participantes: {total_canais}\n\n"
        "Mantenha-se firme para continuar aumentando sua visibilidade, que a semana promete! 💪🚀"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=texto)
        update_views(0)  # Resetando o contador de visualizações
    except Exception as e:
        logger.error(f"Erro ao enviar relatório semanal: {e}")

# Função de boas-vindas personalizada
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Bem-vindo, {user_name}! 🎉\n\n"
        "Para adicionar seu canal, basta tornar o bot administrador. Aproveite os benefícios!"
    )

# Função de simulação de visualização
async def simular_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_views = get_views() + 1
    update_views(total_views)  # Atualiza o banco de dados com o novo número de views
    await update.message.reply_text(f"👀 Mais uma visualização registrada! Total do dia: {total_views} 🎯")

# Função para fazer backup do banco de dados
def backup_db():
    # Backup do banco de dados SQLite
    backup_file = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.db"
    copy('bot_data.db', backup_file)
    print(f"Backup realizado com sucesso: {backup_file}")

# Lista com os chat IDs dos canais onde o bot é administrador
chat_ids = [
    -1002649049975, -1002521735139, -1002649646963, -1002648991007, -1002566487140,
    -1002610733678, -1002631072802, -1002342627563, -1002581311796, -1002645708556,
    -1002261886788, -1002680847721, -1002663744586, -1002576716175, -1002422908996,
    -1002579739516, -1002305906018, -1002608129630, -1002648451435, -1002632167498,
    -1002634219030, -1002659272412, -1002532471834, -1002555455661, -1002694017662,
    -1002619113523, -1002663654523, -1002532598032, -1002569779659, -1002637058718,
    -1002673806655, -1002617005901, -1002591102891, -1002502547461, -1002527153879,
    -1002547163724, -1002686248264, -1002549685600, -1002683098146, -1002521780775,
    -1002496248801, -1002652344851, -1002510129415, -1002524424215, -1002699745337,
    -1002620495214, -1002620603496, -1002670501142, -1002293619562, -1002659153687,
    -1002506650062, -1002689763350, -1002531772113, -1002674038291, -1002670668044,
    -1002673660530, -1002658512135, -1002521019939, -1002370525614, -1002534336418,
    -1002636065794, -1002592699953, -1002626812866, -1002507566931, -1002448809940,
    -1002611400878, -1002674890916, -1002592636698, -1002581071012, -1002676023257,
    -1002555594530, -1002637517683, -1002614028594, -1002521671210, -1002563919969,
    -1002320892399, -1002581354578, -1002535585069, -1002662161329
]

# Função para adicionar os chat IDs ao banco de dados
def add_canais():
    for chat_id in chat_ids:
        add_canal(chat_id)
        logger.info(f"Canal {chat_id} adicionado com sucesso ao banco de dados.")

# Main
async def main():
    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ajustando o pool de conexões e o timeout
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Agendador de tarefas
    scheduler = AsyncIOScheduler()

    # Agendando as mensagens para os horários específicos
    scheduler.add_job(enviar_mensagem_periodica, "cron", hour=10, minute=0, args=[app.bot, "10:00"])
    scheduler.add_job(enviar_mensagem_periodica, "cron", hour=17, minute=0, args=[app.bot, "17:00"])
    scheduler.add_job(enviar_mensagem_periodica, "cron", hour=22, minute=0, args=[app.bot, "22:00"])
    scheduler.add_job(enviar_mensagem_periodica, "cron", hour=3, minute=0, args=[app.bot, "03:00"])

    scheduler.add_job(enviar_relatorio_diario, "cron", hour=0, minute=0, args=[app.bot])
    scheduler.add_job(enviar_relatorio_semanal, "interval", weeks=1, args=[app.bot])
    scheduler.add_job(backup_db, "interval", days=1)  # Backup diário
    scheduler.add_job(verificar_admins_auto, "cron", hour=3, minute=0, args=[app.bot])  # Verificação automática
    scheduler.start()

    # Chama a função para adicionar os canais ao banco de dados
    add_canais()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verificar_admins", verificar_admins))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("visualizacao"), simular_view))

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
