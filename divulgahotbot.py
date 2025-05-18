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
from dotenv import load_dotenv
import pytz

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Aplicar patch para suportar loop reentrante
nest_asyncio.apply()

# === CONFIG ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not ADMIN_ID:
    logger.error("BOT_TOKEN e/ou ADMIN_ID não definidos nas variáveis de ambiente!")
    exit(1)

# Definir o fuso horário de Brasília (GMT-3)
brasilia_tz = pytz.timezone('America/Sao_Paulo')

# Banco de dados SQLite para persistência
def get_db_connection():
    conn = sqlite3.connect('bot_data.db')
    conn.row_factory = sqlite3.Row  # Facilita o acesso aos dados como dicionários
    return conn

def close_db_connection(conn):
    conn.close()

# Função para criar a tabela canais caso não exista
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

# Funções de persistência
def add_canal(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO canais (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    close_db_connection(conn)

def get_canais():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM canais")
    canais = cursor.fetchall()
    close_db_connection(conn)
    return canais

# === ADICIONANDO SEUS CANAIS ===

# Lista dos canais que o bot é administrador
canal_ids = [
    # fanny HOT cont
    -1002649049975, -1002521735139, -1002649646963, -1002648991007, -1002566487140, -1002610733678,
    -1002631072802, -1002342627563, -1002581311796, -1002645708556,

    # fanny irmã conta
    -1002261886788, -1002680847721, -1002663744586, -1002576716175, -1002422908996, -1002579739516,
    -1002305906018, -1002608129630, -1002648451435, -1002632167498,

    # GS
    -1002634219030, -1002659272412, -1002532471834, -1002555455661, -1002694017662, -1002619113523,
    -1002663654523, -1002532598032,

    # CONTA 1 CHANEL
    -1002569779659,

    # CONTA GS MVP
    -1002637058718, -1002673806655, -1002617005901, -1002591102891, -1002502547461, -1002527153879,
    -1002547163724, -1002686248264, -1002549685600, -1002683098146,

    # HOT 20
    -1002521780775, -1002496248801, -1002652344851, -1002510129415, -1002524424215, -1002699745337,
    -1002620495214, -1002620603496, -1002670501142, -1002293619562, -1002659153687, -1002506650062,
    -1002689763350, -1002531772113, -1002674038291, -1002670668044, -1002673660530, -1002658512135,
    -1002521019939, -1002370525614,

    # henrique tele
    -1002534336418, -1002636065794, -1002592699953, -1002626812866, -1002507566931, -1002448809940,
    -1002611400878, -1002674890916, -1002592636698, -1002581071012,

    # ALE CONTA
    -1002676023257, -1002555594530, -1002637517683, -1002614028594, -1002521671210, -1002563919969,
    -1002320892399, -1002581354578, -1002535585069, -1002662161329
]

# Função para adicionar todos os canais ao banco de dados
def adicionar_varios_canais():
    for canal_id in canal_ids:
        add_canal(canal_id)
        logger.info(f"Canal {canal_id} adicionado ao banco de dados.")

# Função para enviar a mensagem personalizada com a lista de canais
async def enviar_mensagem_programada(bot):
    logger.info("Iniciando envio de mensagens programadas...")

    mensagem = (
        "💎: {𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑}\n\n"
        "A MELHOR lista quente do Telegram\n"
        "👇Veja todos os canais disponíveis👇\n\n"
    )

    canais = get_canais()  # Pegando a lista de canais
    buttons = []  # Lista para armazenar os botões

    if not canais:
        logger.warning("Nenhum canal encontrado na base de dados!")
        return

    for canal in canais:
        canal_id = canal[0]  # ID do canal
        
        try:
            chat = await bot.get_chat(canal_id)
            canal_nome = chat.title  # Agora o nome do canal será extraído corretamente

            if chat.username:
                canal_link = f"https://t.me/{chat.username}"
            else:
                canal_link = f"https://t.me/{canal_id}"
        except Exception as e:
            logger.error(f"Erro ao buscar o nome do canal {canal_id}: {e}")
            canal_nome = f"Canal {canal_id}"
            canal_link = f"https://t.me/{canal_id}"

        buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

    for canal in canais:
        canal_id = canal[0]
        try:
            await bot.send_message(chat_id=canal_id, text=mensagem, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
            logger.info(f"Mensagem enviada com sucesso para o canal {canal_id}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")

    logger.info("Mensagens enviadas para todos os canais!")

# Função para iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Comando /start recebido.")
    await update.message.reply_text("Olá! Eu sou o bot e estou pronto para ajudar!")

# Função para enviar a mensagem em horário específico
async def enviar_no_horario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        horario = context.args[0]  # O horário será o primeiro argumento
        hora, minuto = map(int, horario.split(":"))  # Convertendo o horário em hora e minuto

        # Agendando a tarefa para enviar a mensagem no horário escolhido
        scheduler.add_job(enviar_mensagem_programada, 'date', run_date=f"{datetime.now().date()} {hora}:{minuto}:00", args=[update.bot])
        await update.message.reply_text(f"Mensagem agendada para {hora}:{minuto}!")
    except Exception as e:
        await update.message.reply_text(f"Erro ao agendar a mensagem: {e}")

# Inicializando o agendador
scheduler = AsyncIOScheduler()

# Main
async def main():
    logger.info("Iniciando o bot...")

    # Configuração do bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Cria a tabela 'canais' se não existir
    create_tables()

    # Adicionando todos os canais ao banco de dados
    adicionar_varios_canais()

    # Ajustando o pool de conexões e o timeout com a API pública
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Adicionando os handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("enviar", enviar_no_horario))  # Comando /enviar para enviar no horário escolhido

    # Agendando mensagens para horários específicos em horário de Brasília
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=18, minute=0, args=[app.bot], timezone=brasilia_tz)  # 18h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=22, minute=0, args=[app.bot], timezone=brasilia_tz)  # 22h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=4, minute=0, args=[app.bot], timezone=brasilia_tz)   # 4h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=11, minute=0, args=[app.bot], timezone=brasilia_tz)  # 11h
        scheduler.start()
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    logger.info("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
