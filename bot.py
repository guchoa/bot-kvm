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

class GrupoView(discord.ui.View):
    def __init__(self, grupo_numero, criador_id, mensagem):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.criador_id = criador_id
        self.mensagem = mensagem

        classes = list(CLASSES_EMOJIS.items())

        for idx in range(5):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=0,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        for idx in range(5, 10):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=1,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        for idx in range(10, 13):
            classe, emoji_str = classes[idx]
            emoji = self._parse_emoji(emoji_str)
            btn = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                row=2,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            btn.callback = self.gerar_callback(classe)
            self.add_item(btn)

        btn_sair = discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, row=3, custom_id=f"sair_{grupo_numero}")
        btn_fechar = discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, row=3, custom_id=f"fechar_{grupo_numero}")
        btn_recriar = discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, row=3, custom_id=f"recriar_{grupo_numero}")
        btn_apagar = discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, row=3, custom_id=f"apagar_{grupo_numero}")

        btn_sair.callback = self.sair_callback
        btn_fechar.callback = self.fechar_callback
        btn_recriar.callback = self.recriar_callback
        btn_apagar.callback = self.apagar_callback

        self.add_item(btn_sair)
        self.add_item(btn_fechar)
        self.add_item(btn_recriar)
        self.add_item(btn_apagar)

    def _parse_emoji(self, emoji_str):
        if emoji_str.startswith('<:'):
            nome = emoji_str.split(':')[1]
            id = int(emoji_str.split(':')[2][:-1])
            return discord.PartialEmoji(name=nome, id=id, animated=False)
        else:
            return emoji_str

# Comando corrigido para criar grupo sem duplicar
@bot.command()
async def criargrupo(ctx, *, arg=None):
    if arg and '-' in arg:
        try:
            inicio, fim = map(int, arg.split('-'))
            for i in range(inicio, fim + 1):
                await criar_grupo_unico(ctx, i)
        except:
            await ctx.send("Formato inválido. Use !criargrupo 1-3")
    else:
        await criar_grupo_unico(ctx)

async def criar_grupo_unico(ctx, numero=None):
    numeros_existentes = [g['grupo'] for g in grupos_ativos.values() if g['canal_id'] == ctx.channel.id]
    if numero:
        if numero in numeros_existentes:
            await ctx.send(f"Grupo {numero} já existe neste canal.")
            return
        grupo_num = numero
    else:
        for i in range(1, 21):
            if i not in numeros_existentes:
                grupo_num = i
                break
        else:
            await ctx.send("Limite de 20 grupos atingido neste canal.")
            return

    embed = discord.Embed(
        title=f"PT {grupo_num}",
        description="*Sem jogadores ainda.*",
        color=0x2B2D31
    )
    msg = await ctx.send(embed=embed)
    view = GrupoView(grupo_num, ctx.author.id, msg)
    grupos_ativos[msg.id] = {
        'grupo': grupo_num,
        'criador_id': ctx.author.id,
        'jogadores': [],
        'canal_id': ctx.channel.id
    }
    await msg.edit(view=view)
    try:
        await ctx.message.delete()
    except:
        pass

# Comando para limpar todos os grupos no canal atual
@bot.command()
async def limpargrupos(ctx):
    grupos_para_remover = [msg_id for msg_id, g in grupos_ativos.items() if g['canal_id'] == ctx.channel.id]
    for msg_id in grupos_para_remover:
        try:
            msg = await ctx.channel.fetch_message(msg_id)
            await msg.delete()
        except:
            pass
        del grupos_ativos[msg_id]
    await ctx.send("Todos os grupos deste canal foram apagados.", delete_after=10)

# Funções para manter o bot vivo
set_grupos_ativos_func(lambda: grupos_ativos)
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
