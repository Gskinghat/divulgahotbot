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
import pytz
from dotenv import load_dotenv
import random

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
def get_views():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_views FROM views WHERE rowid = 1")
    result = cursor.fetchone()
    close_db_connection(conn)
    return result[0] if result else 0

def update_views(new_views):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE views SET total_views = ? WHERE rowid = 1", (new_views,))
    conn.commit()
    close_db_connection(conn)

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
    logger.info(f"Canais encontrados: {canais}")  # Adicionando log para verificar os canais
    return canais

# Função para verificar se o bot é administrador de múltiplos canais de forma concorrente
async def verificar_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    canais_verificados = []

    async def check_admin(canal):
        try:
            membro = await bot.get_chat_member(canal[0], bot.id)
            if membro.status in ["administrator", "creator"]:
                canais_verificados.append(canal[0])
        except Exception as e:
            logger.error(f"Erro ao verificar {canal[0]}: {e}")

    # Usando asyncio.gather() para realizar as verificações simultaneamente
    await asyncio.gather(*(check_admin(canal) for canal in get_canais()))

    texto = f"✅ Bot é administrador em {len(canais_verificados)} canais públicos."
    await update.message.reply_text(texto)

# Função para enviar a mensagem personalizada com a lista de canais, agora com seleção de 15 canais por vez
async def enviar_mensagem_programada(bot):
    logger.info("Iniciando envio de mensagens programadas...")  # Log para iniciar a tarefa

    # Texto formatado conforme sua solicitação
    mensagem = (
        "💎 𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑\n\n"
        "A MELHOR lista quente do Telegram\n"
        "👇Veja todos os canais disponíveis👇\n\n"
    )

    canais = get_canais()  # Pegando a lista de canais do banco
    if not canais:
        logger.warning("Nenhum canal encontrado na base de dados!")  # Log de alerta se nenhum canal for encontrado
        return

    # Embaralhar a lista de canais para garantir que a seleção seja aleatória
    random.shuffle(canais)

    # Para cada canal da lista de canais cadastrados
    for canal in canais:
        canal_id = canal[0]  # ID do canal

        # Gerando a lista de 15 canais
        buttons = []
        for i in range(15):
            canal_info = canais[i]  # Pegando o canal da lista para adicionar na mensagem

            try:
                # Buscando o nome real do canal
                chat = await bot.get_chat(canal_info[0])
                canal_nome = chat.title  # Nome do canal

                # Verificando se o canal tem um nome de usuário (isso indica que o canal é público)
                if chat.username:
                    canal_link = f"https://t.me/{chat.username}"  # Usando o nome de usuário para canais públicos
                else:
                    canal_link = f"https://t.me/{canal_info[0]}"  # Usando o ID para canais privados

                # Adicionando o botão para o canal
                buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

            except Exception as e:
                # Se ocorrer um erro, loga o erro e usa o fallback
                logger.error(f"Erro ao buscar o nome do canal {canal_info[0]}: {e}")
                canal_nome = f"Canal {canal_info[0]}"  # Caso haja erro, use o ID como fallback
                canal_link = f"https://t.me/{canal_info[0]}"  # Fallback usando o ID interno
                buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

        # Agora, passamos a lista de botões como uma lista de listas
        try:
            await bot.send_message(
                chat_id=canal_id,  # Envia a mensagem para o canal
                text=mensagem,
                reply_markup=InlineKeyboardMarkup(buttons),  # Botões dispostos verticalmente
                parse_mode="Markdown"
            )
            logger.info(f"Mensagem enviada com sucesso para o canal {canal_id}.")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")
            # Adicionar intervalo de 4 segundos antes de tentar enviar para o próximo canal
            await asyncio.sleep(4)  # Espera 4 segundos antes de enviar para o próximo canal

    logger.info("Mensagens enviadas para todos os canais com a lista completa de 15 canais!")

# Função para iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Comando /start recebido.")  # Log para verificar a execução
    await update.message.reply_text("Olá! Eu sou o bot e estou pronto para ajudar!")

# Inicializando o agendador corretamente
scheduler = AsyncIOScheduler()  # Agora o scheduler é inicializado corretamente

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

    # Adicionando canais diretamente ao banco (IDs de canais fornecidos)
    canais_teste = [
        -1002532471834, -1002659272412, -1002694017662, -1002634219030, -1002555455661,
        -1002619113523, -1002532598032, -1002506650062, -1002293619562, -1002531772113,
        -1002689763350, -1002524424215, -1002510129415, -1002620495214, -1002670668044,
        -1002670501142, -1002658512135, -1002699745337, -1002496248801, -1002370525614,
        -1002620603496, -1002521780775, -1002659153687, -1002673660530, -1002652344851,
        -1002674038291, -1002521019939, -1002686248264, -1002591102891, -1002683098146,
        -1002502547461, -1002673806655, -1002549685600, -1002527153879, -1002617005901,
        -1002547163724, -1002637058718, -1002645708556, -1002649646963, -1002610733678,
        -1002631072802, -1002566487140, -1002342627563, -1002581311796, -1002648991007,
        -1002521735139, -1002261886788, -1002680847721, -1002576716175, -1002663744586,
        -1002579739516, -1002422908996, -1002305906018, -1002608129630, -1002648451435,
        -1002632167498, -1002569779659, -1002592699953, -1002592636698, -1002611400878,
        -1002507566931, -1002674890916, -1002581071012, -1002636065794, -1002448809940,
        -1002626812866, -1002534336418
    ]

    for canal_id in canais_teste:
        add_canal(canal_id)

    # Agendando as mensagens para horários específicos em horário de Brasília
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=21, minute=30, args=[app.bot], timezone=brasilia_tz)  # 21:10
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=4, minute=0, args=[app.bot], timezone=brasilia_tz)   # 4h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=11, minute=0, args=[app.bot], timezone=brasilia_tz)  # 11h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=18, minute=20, args=[app.bot], timezone=brasilia_tz)  # 17h
        scheduler.start()  # Iniciando o scheduler
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    logger.info("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True, timeout=30)  # Polling com timeout configurado

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
