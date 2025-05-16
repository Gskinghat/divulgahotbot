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

# Função para enviar mensagem periodicamente
async def enviar_mensagem_periodica(bot, horario):
    mensagem = f"⏰ Hora de se atualizar! A mensagem programada para {horario} foi enviada!"
    # Enviar para o admin ou um grupo específico, aqui estou enviando para o ADMIN_ID
    await bot.send_message(chat_id=ADMIN_ID, text=mensagem)

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
        except Exception as e:
            logger.error(f"Erro ao buscar o nome do canal {canal_id}: {e}")
            canal_nome = f"Canal {canal_id}"  # Caso haja erro, use o ID como fallback

        # Adicionando o botão para cada canal
        buttons.append([InlineKeyboardButton(canal_nome, url=f"https://t.me/{canal_id}")])

    # Criação do teclado com os botões
    keyboard = InlineKeyboardMarkup(buttons)

    # Enviando a mensagem para o canal público
    canal_id = -1002506650062  # Substitua pelo chat_id do seu canal
    mensagem_com_botões = mensagem  # Mensagem com a parte personalizada, sem os botões ainda

    # Envia a mensagem com os botões clicáveis
    await bot.send_message(chat_id=canal_id, text=mensagem_com_botões, reply_markup=keyboard, parse_mode="Markdown")

    print("Mensagem enviada com sucesso!")  # Log para confirmar que a mensagem foi enviada

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

    # Ajustando o pool de conexões e o timeout com a API pública
    app.bot.set_webhook()
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Chama a função para adicionar os canais ao banco de dados
    add_canal(-1002506650062)  # Adicionando um canal de teste (substitua com outros canais conforme necessário)

    # Adiciona o comando para pegar o chat ID
    app.add_handler(CommandHandler("get_chat_id", get_chat_id))

    # Adiciona outros handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verificar_admins", verificar_admins))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("visualizacao"), simular_view))

    # Agendando as mensagens a cada 1 minuto
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", minute="*", args=[app.bot])  # Envia a cada 1 minuto
        scheduler.start()  # Iniciando o scheduler
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Usando asyncio.run diretamente
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
