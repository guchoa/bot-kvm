import os
import logging
from keep_alive import keep_alive

import discord
from discord.ext import commands
import asyncio

logging.basicConfig(level=logging.INFO)

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

        # Linha 0: 5 botões de classe
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

        # Linha 1: 5 botões de classe
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

        # Linha 2: 3 botões de classe
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

        # Linha 3: botões administrativos
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

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id if self.mensagem else None
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Botões sair e classes liberados para todos
        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

        # Só criador pode fechar, recriar, apagar
        if user_id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            msg_id = self.mensagem.id
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            grupo = grupos_ativos.get(msg_id)
            if not grupo:
                await interaction.followup.send("Erro: grupo não encontrado.", ephemeral=True)
                return

            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            grupo['jogadores'].append({
                'id': user.id,
                'nome': nome,
                'classe': classe
            })

            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

            embed = discord.Embed(
                title=f"PT {grupo['grupo']}",
                description=descricao,
                color=0x2B2D31
            )
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

    async def sair_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]

        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("Você não estava nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description=descricao,
            color=0x2B2D31
        )
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    async def fechar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        await self.mensagem.delete()
        grupos_ativos.pop(msg_id, None)
        await interaction.response.send_message("Grupo fechado pelo criador.", ephemeral=True)

    async def recriar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        grupo['jogadores'].clear()

        embed = discord.Embed(
            title=f"PT {grupo['grupo']} (Recriado)",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("Grupo recriado pelo criador.", ephemeral=True)

    async def apagar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        await self.mensagem.delete()
        grupos_ativos.pop(msg_id, None)
        await interaction.response.send_message("Grupo apagado pelo criador.", ephemeral=True)

@bot.command()
async def criargrupo(ctx, intervalo: str):
    try:
        partes = intervalo.split("-")
        inicio = int(partes[0])
        fim = int(partes[1])
    except Exception:
        await ctx.send("Uso correto: !criargrupo 1-3")
        return

    for num in range(inicio, fim + 1):
        embed = discord.Embed(
            title=f"PT {num}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        view = GrupoView(grupo_numero=num, criador_id=ctx.author.id, mensagem=None)
        mensagem = await ctx.send(embed=embed, view=view)
        view.mensagem = mensagem

        grupos_ativos[mensagem.id] = {
            'grupo': num,
            'criador_id': ctx.author.id,
            'jogadores': []
        }

    await ctx.message.delete()

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpargrupos(ctx):
    canal = ctx.channel
    msgs_apagadas = 0
    to_remove = []

    async for msg in canal.history(limit=100):
        if msg.id in grupos_ativos:
            try:
                await msg.delete()
                to_remove.append(msg.id)
                msgs_apagadas += 1
            except discord.Forbidden:
                await ctx.send("Não tenho permissão para apagar mensagens aqui.", delete_after=10)
                return
            except Exception as e:
                await ctx.send(f"Erro ao apagar mensagem: {e}", delete_after=10)
                return

    for msg_id in to_remove:
        grupos_ativos.pop(msg_id, None)

    await ctx.send(f"🧹 Limpeza feita! {msgs_apagadas} grupos apagados neste canal.", delete_after=10)

@bot.event
async def on_ready():
    logging.info(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')

keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

async def start_bot():
    retry_delay = 5
    max_delay = 300
    tentativas = 0
    max_tentativas = 10
    while tentativas < max_tentativas:
        try:
            logging.info("Tentando conectar no Discord...")
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            tentativas += 1
            logging.info(f"Tentativa {tentativas}/{max_tentativas} - Repetindo conexão em {retry_delay} segundos...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
        else:
            logging.info("Bot desconectado normalmente.")
            break
    else:
        logging.error("Número máximo de tentativas atingido. Encerrando o bot.")

if __name__ == "__main__":
    asyncio.run(start_bot())
