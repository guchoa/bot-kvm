import os
import logging
from keep_alive import keep_alive

import discord
from discord.ext import commands
import asyncio

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CLASSES = [
    ("sacerdote", "🟡", 0),
    ("monge", "🟨", 0),
    ("cacador", "🟢", 0),
    ("bardo", "🟩", 0),
    ("odalisca", "🟩", 1),
    ("cavaleiro", "🔴", 1),
    ("templario", "🟥", 1),
    ("bruxo", "🔵", 1),
    ("sabio", "🟦", 2),
    ("ferreiro", '<:bolinha_ciano:1391827989267878030>', 2),
    ("alquimista", '<:quadrado_ciano:1391827991218225244>', 2),
    ("assassino", "🟣", 2),
    ("arruaceiro", "🟪", 2)
]


grupos_ativos = {}

class GrupoView(discord.ui.View):
    def __init__(self, grupo_numero, criador_id=None, mensagem=None):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.criador_id = criador_id
        self.mensagem = mensagem

        for classe, emoji_str, row in CLASSES:
            if emoji_str.startswith('<:'):
                nome = emoji_str.split(':')[1]
                id = int(emoji_str.split(':')[2][:-1])
                emoji = discord.PartialEmoji(name=nome, id=id)
            else:
                emoji = emoji_str

            self.add_item(ClasseButton(classe, emoji, row))

        self.add_item(SairButton(row=3))
        self.add_item(FecharButton(row=3))
        self.add_item(RecriarButton(row=3))
        self.add_item(ApagarButton(row=3))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        if custom_id in [c[0] for c in CLASSES] or custom_id == "sair":
            return True

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        return True

class ClasseButton(discord.ui.Button):
    def __init__(self, classe, emoji, row):
        super().__init__(label=classe.capitalize(), emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=classe, row=row)
        self.classe = classe

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        msg_id = self.view.mensagem.id
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

        grupo['jogadores'].append({ 'id': user.id, 'nome': nome, 'classe': self.classe })

        linhas = [f"{dict(CLASSES)[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
        await self.view.mensagem.edit(embed=embed, view=self.view)
        await interaction.followup.send(f"Você entrou como **{self.classe.capitalize()}**!", ephemeral=True)

class SairButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id="sair", row=row)

    async def callback(self, interaction: discord.Interaction):
        msg_id = self.view.mensagem.id
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

        linhas = [f"{dict(CLASSES)[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
        await self.view.mensagem.edit(embed=embed, view=self.view)
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

class FecharButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, custom_id="fechar", row=row)

    async def callback(self, interaction: discord.Interaction):
        for item in self.view.children:
            item.disabled = True
        await self.view.mensagem.edit(view=self.view)
        await interaction.response.send_message("Grupo fechado para novas inscrições.", ephemeral=True)

class RecriarButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, custom_id="recriar", row=row)

    async def callback(self, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.view.mensagem.id)
        novo_embed = discord.Embed(title=f"PT {grupo['grupo']}", description="*Sem jogadores ainda.*", color=0x2B2D31)
        nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=grupo['criador_id'])
        nova_msg = await self.view.mensagem.channel.send(embed=novo_embed, view=nova_view)
        nova_view.mensagem = nova_msg
        grupos_ativos[nova_msg.id] = {
            'grupo': grupo['grupo'],
            'jogadores': [],
            'criador_id': grupo['criador_id'],
            'mensagem': nova_msg
        }
        await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)

class ApagarButton(discord.ui.Button):
    def __init__(self, row):
        super().__init__(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, custom_id="apagar", row=row)

    async def callback(self, interaction: discord.Interaction):
        msg_id = self.view.mensagem.id
        grupos_ativos.pop(msg_id, None)
        await self.view.mensagem.delete()
        await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        logging.info(f"Comando !criargrupo recebido de {ctx.author}")

        if '-' in intervalo:
            inicio, fim = map(int, intervalo.split('-'))
            numeros = range(inicio, fim + 1)
        else:
            numero = int(intervalo)
            numeros = [numero]

        await ctx.message.delete()

        for numero in numeros:
            embed = discord.Embed(title=f"PT {numero}", description="*Sem jogadores ainda.*", color=0x2B2D31)
            view = GrupoView(grupo_numero=numero, criador_id=ctx.author.id)
            mensagem = await ctx.send(embed=embed, view=view)
            view.mensagem = mensagem
            bot.add_view(view)  # garante funcionamento pós-restart

            grupos_ativos[mensagem.id] = {
                'grupo': numero,
                'jogadores': [],
                'criador_id': ctx.author.id,
                'mensagem': mensagem
            }

            logging.info(f"Grupo PT {numero} criado.")
            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"Erro inesperado ao criar grupo: {e}")
        await ctx.send("❌ Ocorreu um erro ao criar o grupo. Verifique os logs.")

@bot.event
async def on_ready():
    logging.info(f"Bot está online! Logado como {bot.user} (ID: {bot.user.id})")

keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("ERRO: variável de ambiente DISCORD_BOT_TOKEN não encontrada.")
    exit(1)

async def start_bot():
    retry_delay = 5
    while True:
        try:
            await bot.start(TOKEN)
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            await asyncio.sleep(retry_delay)

if __name__ == "__main__":
    asyncio.run(start_bot())
