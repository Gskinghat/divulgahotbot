from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Importando o AsyncIOScheduler
import pytz
import traceback
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Definir o fuso horário de Brasília (GMT-3)
brasilia_tz = pytz.timezone('America/Sao_Paulo')

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

# Função para calcular visualizações e enviar relatório
async def simular_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    total_visualizacoes = 0
    relatorio = "📊 Relatório de Visualizações dos Canais:\n\n"

    canais = get_canais()  # Pegando a lista de canais
    if not canais:
        await bot.send_message(chat_id=ADMIN_ID, text="Nenhum canal registrado para visualizar.")
        return

    for canal in canais:
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

