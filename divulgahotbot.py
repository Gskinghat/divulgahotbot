import asyncio
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
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

# Função para adicionar canais via comando
def add_canal(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO canais (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    close_db_connection(conn)

# Função para pegar todos os canais
def get_canais():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM canais")
    canais = cursor.fetchall()
    close_db_connection(conn)
    return canais

# Função para enviar a mensagem personalizada com a lista de canais
async def enviar_mensagem_programada(bot):
    mensagem = (
        "💎: {𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑}\n\n"
        "A MELHOR lista quente do Telegram\n"
        "👇Veja todos os canais disponíveis👇\n\n"
    )

    canais = get_canais()  # Pegando a lista de canais
    buttons = []  # Lista para armazenar os botões

    if not canais:
        logger.warning("Nenhum canal encontrado na base de dados!")  # Log de alerta se nenhum canal for encontrado
        return

    for canal in canais:
        canal_id = canal[0]  # ID do canal
        
        try:
            # Buscando o nome real do canal
            chat = await bot.get_chat(canal_id)
            canal_nome = chat.title  # Agora o nome do canal será extraído corretamente

            # Verificando se o canal tem um nome de usuário (isso indica que o canal é público)
            if chat.username:
                canal_link = f"https://t.me/{chat.username}"  # Usando o nome de usuário para canais públicos
            else:
                canal_link = f"https://t.me/{canal_id}"  # Usando o ID para canais privados
        except Exception as e:
            logger.error(f"Erro ao buscar o nome do canal {canal_id}: {e}")
            canal_nome = f"Canal {canal_id}"  # Caso haja erro, use o ID como fallback
            canal_link = f"https://t.me/{canal_id}"  # Fallback usando o ID interno

        buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

    # Enviando a mensagem para todos os canais cadastrados
    for canal in canais:
        canal_id = canal[0]
        try:
            # Envia a mensagem para o canal
            await bot.send_message(chat_id=canal_id, text=mensagem, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
            logger.info(f"Mensagem enviada com sucesso para o canal {canal_id}")  # Log de sucesso
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")

# Função para iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Comando /start recebido.")  # Log para verificar a execução
    await update.message.reply_text("Olá! Eu sou o bot e estou pronto para ajudar!")

# Inicializando o agendador corretamente
scheduler = AsyncIOScheduler()

# Main
async def main():
    logger.info("Iniciando o bot...")  # Log para verificar o início da execução

    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Chama a função para criar a tabela 'canais' se não existir
    create_tables()

    # Ajustando o pool de conexões e o timeout com a API pública
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Adicionando o comando de verificação de admin
    app.add_handler(CommandHandler("verificar_admins", verificar_admins))

    # Adicionando o comando /start
    app.add_handler(CommandHandler("start", start))  # Comando start agora registrado

    # Adicionando o comando para gerar relatório de visualizações
    app.add_handler(CommandHandler("relatorio_views", gerar_relatorio_views))

    # Agendando as mensagens para horários específicos em horário de Brasília
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=18, minute=0, args=[app.bot], timezone=brasilia_tz)  # 18h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=22, minute=0, args=[app.bot], timezone=brasilia_tz)  # 22h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=4, minute=0, args=[app.bot], timezone=brasilia_tz)   # 4h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=11, minute=0, args=[app.bot], timezone=brasilia_tz)  # 11h
        scheduler.start()  # Iniciando o scheduler
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    logger.info("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)  # Apenas polling, sem webhook

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
