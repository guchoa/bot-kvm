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

CLASSES_EMOJIS = {
    'sacerdote': '🟡',
    'monge': '🟨',
    'cacador': '🟢',
    'bardo': '🟩',
    'odalisca': '🟩',
    'cavaleiro': '🔴',
    'templario': '🟥',
    'bruxo': '🔵',  # blue circle para bruxo
    'sabio': '🟦',
    'ferreiro': '<:bolinha_ciano:1391827989267878030>',
    'alquimista': '<:quadrado_ciano:1391827991218225244>',
    'assassino': '🟣',
    'arruaceiro': '🟪'
}

grupos_ativos = {}

class GrupoView(discord.ui.View):
    def __init__(self, grupo_numero, criador_id=None, mensagem=None):
        super().__init__(timeout=None)
        self.grupo_numero = grupo_numero
        self.criador_id = criador_id
        self.mensagem = mensagem

        for classe, emoji_str in CLASSES_EMOJIS.items():
            if emoji_str.startswith('<:'):
                nome = emoji_str.split(':')[1]
                id = int(emoji_str.split(':')[2][:-1])
                emoji = discord.PartialEmoji(name=nome, id=id, animated=False)
            else:
                emoji = emoji_str

            button = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=classe
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)

        self.add_item(discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id="sair"))
        self.add_item(discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, custom_id="fechar"))
        self.add_item(discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, custom_id="recriar"))
        self.add_item(discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, custom_id="apagar"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        grupo = grupos_ativos.get(self.mensagem.id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        if custom_id in CLASSES_EMOJIS.keys() or custom_id == "sair":
            await self.handle_interaction(interaction, custom_id)
            return False

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        await self.handle_interaction(interaction, custom_id)
        return False

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            grupo = grupos_ativos.get(self.mensagem.id)
            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]
            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            grupo['jogadores'].append({'id': user.id, 'nome': nome, 'classe': classe})
            await self.atualizar_embed()
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

    async def handle_interaction(self, interaction: discord.Interaction, custom_id: str):
        if custom_id == "sair":
            await self.sair(interaction)
        elif custom_id == "fechar":
            await self.fechar(interaction)
        elif custom_id == "recriar":
            await self.recriar(interaction)
        elif custom_id == "apagar":
            await self.apagar(interaction)

    async def atualizar_embed(self):
        grupo = grupos_ativos.get(self.mensagem.id)
        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"
        embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
        await self.mensagem.edit(embed=embed, view=self)

    async def sair(self, interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        user_id = interaction.user.id
        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]
        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("Você não estava nesse grupo.", ephemeral=True)
            return
        await self.atualizar_embed()
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    async def fechar(self, interaction):
        for item in self.children:
            item.disabled = True
        await self.mensagem.edit(view=self)
        await interaction.response.send_message("Grupo fechado para novas inscrições.", ephemeral=True)

    async def recriar(self, interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        novo_embed = discord.Embed(title=f"PT {grupo['grupo']}", description="*Sem jogadores ainda.*", color=0x2B2D31)
        nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=grupo['criador_id'])
        nova_msg = await self.mensagem.channel.send(embed=novo_embed, view=nova_view)
        nova_view.mensagem = nova_msg
        grupos_ativos[nova_msg.id] = {
            'grupo': grupo['grupo'],
            'jogadores': [],
            'criador_id': grupo['criador_id'],
            'mensagem': nova_msg
        }
        await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)

    async def apagar(self, interaction):
        grupos_ativos.pop(self.mensagem.id, None)
        await self.mensagem.delete()
        await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        logging.info(f"Comando !criargrupo recebido de {ctx.author}")
        if '-' in intervalo:
            inicio, fim = map(int, intervalo.split('-'))
            if not (1 <= inicio <= 20 and 1 <= fim <= 20) or inicio > fim:
                await ctx.send("Intervalo inválido. Use números entre 1 e 20.")
                return
            numeros = range(inicio, fim + 1)
        else:
            numero = int(intervalo)
            if not (1 <= numero <= 20):
                await ctx.send("Número de PT inválido. Use entre 1 e 20.")
                return
            numeros = [numero]

        try:
            await ctx.message.delete()
        except Exception as e:
            logging.warning(f"Não foi possível deletar a mensagem de comando: {e}")

        for numero in numeros:
            embed = discord.Embed(title=f"PT {numero}", description="*Sem jogadores ainda.*", color=0x2B2D31)
            view = GrupoView(grupo_numero=numero, criador_id=ctx.author.id)
            mensagem = await ctx.send(embed=embed, view=view)
            view.mensagem = mensagem
            grupos_ativos[mensagem.id] = {
                'grupo': numero,
                'jogadores': [],
                'criador_id': ctx.author.id,
                'mensagem': mensagem
            }
            logging.info(f"Grupo PT {numero} criado.")
            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"Erro ao criar grupo: {e}")
        await ctx.send("Erro ao criar grupo. Verifique os logs.")

@bot.event
async def on_guild_join(guild):
    await garantir_cargo_bot(guild)

@bot.event
async def on_ready():
    logging.info(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')
    for guild in bot.guilds:
        await garantir_cargo_bot(guild)

async def garantir_cargo_bot(guild):
    nome_cargo = "Bot KVM"
    cargo = discord.utils.get(guild.roles, name=nome_cargo)
    if not cargo:
        try:
            cargo = await guild.create_role(
                name=nome_cargo,
                permissions=discord.Permissions.all(),
                color=discord.Color.teal(),
                reason="Cargo padrão para o bot com todas permissões"
            )
        except Exception as e:
            logging.warning(f"Erro ao criar cargo em {guild.name}: {e}")
            return
    bot_member = guild.get_member(bot.user.id)
    if bot_member and cargo not in bot_member.roles:
        try:
            await bot_member.add_roles(cargo)
        except Exception as e:
            logging.warning(f"Erro ao atribuir cargo em {guild.name}: {e}")

keep_alive()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    logging.error("Token não encontrado.")
    exit(1)

async def start_bot():
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(start_bot())
