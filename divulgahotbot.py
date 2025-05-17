import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import sqlite3
import os
from dotenv import load_dotenv

# Carregar as variáveis de ambiente do .env
load_dotenv()

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar as variáveis do arquivo .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    logger.error("BOT_TOKEN ou ADMIN_ID não definidos no .env ou no painel do Railway!")
    exit(1)

# Definir o fuso horário de Brasília (GMT-3)
brasilia_tz = pytz.timezone('America/Sao_Paulo')

# Função para criar as tabelas caso não existam
def create_tables():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS canais (
        chat_id INTEGER PRIMARY KEY
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS views (
        rowid INTEGER PRIMARY KEY AUTOINCREMENT,
        total_views INTEGER
    )
    ''')
    conn.commit()
    conn.close()

# Função para obter os canais do banco de dados
def get_canais():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM canais")
    canais = cursor.fetchall()
    conn.close()
    return canais

# Função para verificar se o bot é administrador em todos os canais
async def verificar_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    canais_verificados = []

    # Recupera todos os canais do banco de dados
    canais = get_canais()

    # Verifica se o bot é administrador em cada canal
    for canal in canais:
        canal_id = canal[0]
        try:
            # Verifica o status do bot no canal
            membro = await bot.get_chat_member(canal_id, bot.id)
            if membro.status in ["administrator", "creator"]:
                canais_verificados.append(canal_id)
        except Exception as e:
            logger.error(f"Erro ao verificar o status do bot no canal {canal_id}: {e}")

    # Envia mensagem para o admin com os canais onde o bot é administrador
    if canais_verificados:
        canais_listados = "\n".join([f"Canal: {canal_id}" for canal_id in canais_verificados])
        await update.message.reply_text(f"✅ O bot é administrador nos seguintes canais:\n{canais_listados}")
    else:
        await update.message.reply_text("❌ O bot não é administrador em nenhum dos canais registrados.")

# Função para enviar a mensagem personalizada com a lista de canais
async def enviar_mensagem_programada(bot):
    print("Tentando enviar a mensagem...")  # Log para verificar se a função está sendo chamada

    # Cabeçalho da mensagem personalizada
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
            logger.error(f"Detalhes do erro: {traceback.format_exc()}")  # Mostrando o traceback completo
            canal_nome = f"Canal {canal_id}"  # Caso haja erro, use o ID como fallback
            canal_link = f"https://t.me/{canal_id}"  # Fallback usando o ID interno

        buttons.append([InlineKeyboardButton(canal_nome, url=canal_link)])

    # Enviando a mensagem para todos os canais cadastrados
    for canal in canais:
        canal_id = canal[0]
        try:
            # Envia a mensagem para o canal
            await bot.send_message(chat_id=canal_id, text=mensagem, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
            print(f"Mensagem enviada com sucesso para o canal {canal_id}")  # Log de sucesso
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o canal {canal_id}: {e}")
            logger.error(f"Detalhes do erro: {traceback.format_exc()}")  # Log detalhado do erro

    print("Mensagens enviadas para todos os canais!")  # Log para confirmar que a mensagem foi enviada para todos os canais

# Função para iniciar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Eu sou o bot e estou pronto para ajudar!")

# Função principal do bot
async def main():
    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Chama a função para criar a tabela 'canais' e 'views' se não existirem
    create_tables()

    # Ajustando o pool de conexões e o timeout com a API pública
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Adicionando o comando de verificação de admin
    app.add_handler(CommandHandler("verificar_admins", verificar_admins))

    # Agendando as mensagens para horários específicos em horário de Brasília
    try:
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=18, minute=0, args=[app.bot], timezone=brasilia_tz)  # 18h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=22, minute=0, args=[app.bot], timezone=brasilia_tz)  # 22h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=4, minute=0, args=[app.bot], timezone=brasilia_tz)   # 4h
        scheduler.add_job(enviar_mensagem_programada, "cron", hour=11, minute=0, args=[app.bot], timezone=brasilia_tz)  # 11h
        scheduler.start()  # Iniciando o scheduler
    except Exception as e:
        logger.error(f"Erro ao agendar tarefa: {e}")

    print("✅ Bot rodando com polling e agendamento diário!")
    await app.run_polling(drop_pending_updates=True)  # Apenas polling, sem webhook

if __name__ == "__main__":
    try:
        main()  # Remover o uso de asyncio.run() e simplesmente chamar main()
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
