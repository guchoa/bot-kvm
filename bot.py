import os
import logging
import asyncio
import discord
from discord.ext import commands
from keep_alive import keep_alive, set_grupos_ativos_func

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

CLASSES_EMOJIS = {
    'sacerdote': '🟡',
    'monge': '🟨',
    'cacador': '🟢',
    'bardo': '🟩',
    'odalisca': '🟩',
    'cavaleiro': '🔴',
    'templario': '🟥',
    'bruxo': '🔵',
    'sabio': '🟦',
    'ferreiro': '<:bolinha_ciano:1391827989267878030>',
    'alquimista': '<:quadrado_ciano:1391827991218225244>',
    'assassino': '🟣',
    'arruaceiro': '🟪'
}

grupos_ativos = {}

# ... (restante da classe GrupoView permanece igual)

@bot.command()
async def criargrupo(ctx):
    canal_id = ctx.channel.id
    criador_id = ctx.author.id

    # Determina o menor número de grupo disponível (de 1 a 20)
    grupo_existentes = {info['grupo'] for info in grupos_ativos.values()}
    grupo_num = next((i for i in range(1, 21) if i not in grupo_existentes), None)

    if grupo_num is None:
        await ctx.send("❌ Todos os grupos de 1 a 20 já estão criados.")
        return

    embed = discord.Embed(
        title=f"PT {grupo_num}",
        description="*Sem jogadores ainda.*",
        color=0x2B2D31
    )
    msg = await ctx.send(embed=embed)
    view = GrupoView(grupo_num, criador_id, msg)
    grupos_ativos[msg.id] = {
        'grupo': grupo_num,
        'criador_id': criador_id,
        'jogadores': [],
        'canal_id': canal_id
    }
    await msg.edit(view=view)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def limpargrupos(ctx):
    canal = ctx.channel
    deletados = 0
    for msg_id in list(grupos_ativos.keys()):
        grupo = grupos_ativos[msg_id]
        if grupo['canal_id'] == canal.id:
            try:
                msg = await canal.fetch_message(msg_id)
                await msg.delete()
                deletados += 1
            except:
                pass
            del grupos_ativos[msg_id]

    await ctx.send(f"🗑️ {deletados} grupo(s) apagado(s) com sucesso.", delete_after=5)
    try:
        await ctx.message.delete()
    except:
        pass

def get_grupos():
    return grupos_ativos

set_grupos_ativos_func(get_grupos)
keep_alive()

async def start_bot():
    retry_delay = 5
    max_delay = 300
    attempts = 0
    max_attempts = 10
    while attempts < max_attempts:
        try:
            logging.info("Tentando conectar no Discord...")
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            attempts += 1
            logging.info(f"Tentativa {attempts}/{max_attempts} - Tentando reconectar em {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
        else:
            logging.info("Bot desconectado normalmente.")
            break
    else:
        logging.error("Número máximo de tentativas atingido. Encerrando o bot.")

if __name__ == "__main__":
    asyncio.run(start_bot())
