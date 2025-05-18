import logging
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz
import asyncio
import os
from dotenv import load_dotenv

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregando variáveis de ambiente
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6835008287  # ID do administrador

# Definindo o fuso horário de Brasília
brasilia_tz = pytz.timezone('America/Sao_Paulo')

# Inicializando o agendador
scheduler = AsyncIOScheduler(timezone=brasilia_tz)
scheduler.start()

# Banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row  # Facilita o acesso aos dados como dicionários
    return conn

def close_db_connection(conn):
    conn.close()

# Função para criar a tabela 'canais' caso não exista
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canais (
        chat_id INTEGER PRIMARY KEY
    )
    """)
    conn.commit()
    close_db_connection(conn)

# Função para obter canais cadastrados
def get_canais():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM canais")
    canais = cursor.fetchall()
    close_db_connection(conn)
    return canais

# Função para adicionar um canal no banco de dados
def add_canal(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO canais (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    close_db_connection(conn)

# Função para enviar mensagens programadas
async def enviar_mensagem_programada(bot):
    logger.info("Iniciando envio de mensagens programadas...")
    canais = get_canais()  # Pegando a lista de canais
    mensagem = "💎: {𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑}\n\nA MELHOR lista quente do Telegram\n👇Veja todos os canais disponíveis👇\n\n"
    
    if not canais:
        logger.warning("Nenhum canal encontrado na base de dados!")
        return

    for canal in canais:
        canal_id = canal[0]
        try:
            await bot.send_message(chat_id=canal_id, text=mensagem)
            logger.info(f"Mensagem enviada para o canal {canal_id}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")

# Função para agendar mensagens
async def agendar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Você não tem permissão para agendar mensagens.")
        return

    try:
        # Adicionando o agendamento para o envio de mensagens nos horários especificados
        scheduler.add_job(enviar_mensagem_programada, 'cron', hour=18, minute=0, args=[context.bot], timezone=brasilia_tz)
        scheduler.add_job(enviar_mensagem_programada, 'cron', hour=22, minute=0, args=[context.bot], timezone=brasilia_tz)
        scheduler.add_job(enviar_mensagem_programada, 'cron', hour=4, minute=0, args=[context.bot], timezone=brasilia_tz)
        scheduler.add_job(enviar_mensagem_programada, 'cron', hour=11, minute=0, args=[context.bot], timezone=brasilia_tz)

        await update.message.reply_text("Mensagens programadas com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao agendar a mensagem: {e}")
        await update.message.reply_text("Houve um erro ao tentar agendar as mensagens.")

# Função para listar os canais onde o bot é administrador
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

# Função start do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado! Use o comando '/agendar' para agendar mensagens.")

# Função para inicializar e rodar o bot
async def main():
    logger.info("Iniciando o bot...")

    # Criação das tabelas caso não existam
    create_tables()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Adiciona o handler para os comandos
    app.add_handler(CommandHandler("agendar", agendar_mensagem))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verificar_admins", verificar_admins))  # Para verificar a administração dos canais

    # Inicia o bot
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
