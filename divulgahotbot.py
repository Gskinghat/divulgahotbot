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

if not BOT_TOKEN or not ADMIN_ID:
    logger.error("BOT_TOKEN e/ou ADMIN_ID não definidos nas variáveis de ambiente!")
    exit(1)

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
    return canais

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

# Função para obter o chat_id
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id  # Obtém o chat_id do comando de start
    await update.message.reply_text(f"Seu chat_id é: {chat_id}")

# Função para adicionar canais via comando
async def add_canal_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificar se o comando foi enviado por um admin
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Você não tem permissão para adicionar canais.")
        return

    # Verificar se foi fornecido um ID de canal
    if not context.args:
        await update.message.reply_text("Por favor, forneça o ID do canal para adicionar.")
        return

    canal_id = context.args[0]  # O ID do canal será o primeiro argumento

    try:
        canal_id = int(canal_id)  # Certificar-se de que o ID é um número inteiro
        add_canal(canal_id)
        await update.message.reply_text(f"Canal {canal_id} adicionado com sucesso!")
    except ValueError:
        await update.message.reply_text("O ID do canal deve ser um número válido.")

# Função para adicionar todos os canais novamente
def adicionar_varios_canais():
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

    for canal_id in canal_ids:
        add_canal(canal_id)
        logger.info(f"Canal {canal_id} adicionado ao banco de dados.")

# Função para enviar a mensagem personalizada com a lista de canais
async def enviar_mensagem_programada(bot):
    print("Tentando enviar a mensagem...")  # Log para verificar se a função está sendo chamada

    # Cabeçalho da mensagem personalizada
    mensagem = (
        "💎: {𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑}\n\n"
        "A MELHOR lista quente do Telegram\n"
        "👇Veja todos os canais disponíveis👇\n\n"
    )

    # Adicionando a lista de canais à mensagem no formato desejado
    canais = get_canais()  # Pegando a lista de canais
    buttons = []  # Lista para armazenar os botões

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

        # Adicionando o botão para cada canal, agora com o nome real e link correto
        buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

        try:
            # Enviando a mensagem para o canal
            await bot.send_message(chat_id=canal_id, text=mensagem, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
            print(f"Mensagem enviada com sucesso para o canal {canal_id}")  # Log de sucesso
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")

    print("Mensagens enviadas para todos os canais!")  # Log para confirmar que a mensagem foi enviada para todos os canais

# Função para calcular visualizações e enviar relatório
async def simular_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    total_visualizacoes = 0
    relatorio = "📊 Relatório de Visualizações dos Canais:\n\n"

    for canal in get_canais():
        canal_id = canal[0]
        try:
            # Simulando o cálculo de visualizações (isso pode ser um número fixo ou calculado de alguma maneira)
            visualizacoes = 100  # Aqui você pode implementar o cálculo real
            total_visualizacoes += visualizacoes
            relatorio += f"Canal {canal_id}: {visualizacoes} visualizações\n"
        except Exception as e:
            logger.error(f"Erro ao calcular visualizações para {canal[0]}: {e}")

    relatorio += f"\nTotal de Visualizações: {total_visualizacoes}"
    await bot.send_message(chat_id=ADMIN_ID, text=relatorio)

# Função para iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Eu sou o bot e estou pronto para ajudar!")

# Inicializando o agendador corretamente
scheduler = AsyncIOScheduler()  # Agora o scheduler é inicializado corretamente

# Main
async def main():
    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Chama a função para criar a tabela 'canais' se não existir
    create_tables()

    # Chama a função para adicionar todos os canais novamente
    adicionar_varios_canais()

    # Ajustando o pool de conexões e o timeout com a API pública
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Agendando as mensagens para horários específicos
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=18, minute=0, args=[app.bot])  # 18h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=22, minute=0, args=[app.bot])  # 22h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=4, minute=0, args=[app.bot])   # 4h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=11, minute=0, args=[app.bot])  # 11h
        scheduler.start()  # Iniciando o scheduler
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)  # Apenas polling, sem webhook

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
