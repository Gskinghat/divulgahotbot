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
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Aqui é onde o scheduler é importado
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

# Função para obter o chat_id do grupo
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Este é o chat ID do grupo: {chat_id}")

# Função para enviar a mensagem personalizada com a lista de canais
async def enviar_mensagem_programada(bot):
    hoje = datetime.now().strftime("%d/%m/%Y")
    total_views = get_views()
    total_canais = len(get_canais())

    # Parte personalizada da mensagem
    mensagem = (
        "💎: {𝗟 𝗜 𝗦 𝗧 𝗔 𝗛𝗢𝗧 🔞👑}\n\n"
        "A MELHOR lista quente do Telegram\n"
        "👇Veja todos os canais disponíveis👇\n\n"
    )

    # Adicionando a lista de canais à mensagem
    canais = get_canais()
    for canal in canais:
        canal_id = canal[0]  # ID do canal
        canal_nome = f"Canal {canal_id}"  # Nome do canal ou outra informação que você deseja exibir
        mensagem += f"🔗 {canal_nome}: https://t.me/{canal_id}\n"

    # Enviando a mensagem para o canal público
    canal_id = -1002506650062  # Substitua pelo chat_id do seu canal
    await bot.send_message(chat_id=canal_id, text=mensagem, parse_mode="Markdown")

# Main
async def main():
    # Configuração do bot com pool e timeout ajustados
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ajustando o pool de conexões e o timeout
    app.bot._request_kwargs = {
        'timeout': 30,  # Timeout de 30 segundos
        'pool_size': 20  # Pool de conexões de 20
    }

    # Inicializando o agendador corretamente
    scheduler = AsyncIOScheduler()  # Agora o scheduler é inicializado corretamente

    # Adicionando as tarefas no agendador
    scheduler.add_job(enviar_mensagem_programada, "cron", hour=10, minute=0, args=[app.bot])  # Alterar horário conforme necessidade
    scheduler.start()  # Iniciando o scheduler

    # Chama a função para adicionar os canais ao banco de dados
    add_canal(-1002506650062)  # Adicionando um canal de teste (substitua com outros canais conforme necessário)

    # Adiciona o comando para pegar o chat ID
    app.add_handler(CommandHandler("get_chat_id", get_chat_id))

    # Adiciona outros handlers
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
