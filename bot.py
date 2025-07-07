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

# Emojis corrigidos com PartialEmoji
CLASSES_EMOJIS = {
    'sacerdote': '🟡',
    'monge': '🟨',
    'cacador': '🟢',
    'bardo': '🟩',
    'odalisca': '🟩',
    'cavaleiro': '🔴',
    'templario': '🟥',
    'bruxo': '🔸',
    'sabio': '🟦',
    'ferreiro': discord.PartialEmoji(name="bolinha_ciano", id=1391817828415443099),
    'alquimista': discord.PartialEmoji(name="quadrado_ciano", id=1391817845364494507),
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

        for classe, emoji in CLASSES_EMOJIS.items():
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
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        if custom_id == "sair":
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]
            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"
            embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)
            return False

        if grupo['criador_id'] != user_id:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        if custom_id == "fechar":
            for item in self.children:
                item.disabled = True
            await self.mensagem.edit(view=self)
            await interaction.response.send_message(f"O grupo PT {grupo['grupo']} foi fechado para novas inscrições.", ephemeral=True)
            return False

        if custom_id == "apagar":
            await self.mensagem.delete()
            grupos_ativos.pop(msg_id, None)
            await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)
            return False

        if custom_id == "recriar":
            novo_embed = discord.Embed(title=f"PT {grupo['grupo']}", description="*Sem jogadores ainda.*", color=0x2B2D31)
            nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=user_id)
            nova_msg = await self.mensagem.channel.send(embed=novo_embed, view=nova_view)
            nova_view.mensagem = nova_msg
            grupos_ativos[nova_msg.id] = {
                'grupo': grupo['grupo'],
                'jogadores': [],
                'criador_id': user_id,
                'mensagem': nova_msg
            }
            await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)
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

            if any(j['id'] == user.id for j in grupo['jogadores']):
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

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        if '-' in intervalo:
            inicio, fim = map(int, intervalo.split('-'))
            if not (1 <= inicio <= 20 and 1 <= fim <= 20) or inicio > fim:
                await ctx.send("Intervalo inválido. Use números entre 1 e 20, como !criargrupo 1-5.")
                return
            numeros = range(inicio, fim + 1)
        else:
            numero = int(intervalo)
            if not (1 <= numero <= 20):
                await ctx.send("Número de PT inválido. Use um número entre 1 e 20.")
                return
            numeros = [numero]
    except ValueError:
        await ctx.send("Formato inválido. Use !criargrupo 1 ou !criargrupo 1-5.")
        return

    await ctx.message.delete()

    for numero in numeros:
        embed = discord.Embed(
            title=f"PT {numero}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        view = GrupoView(grupo_numero=numero, criador_id=ctx.author.id)
        mensagem = await ctx.send(embed=embed, view=view)
        view.mensagem = mensagem

        grupos_ativos[mensagem.id] = {
            'grupo': numero,
            'jogadores': [],
            'criador_id': ctx.author.id,
            'mensagem': mensagem
        }

        await asyncio.sleep(1)

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
        logging.info(f"Criando cargo '{nome_cargo}' em {guild.name}...")
        try:
            cargo = await guild.create_role(
                name=nome_cargo,
                permissions=discord.Permissions(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True,
                    use_application_commands=True,
                    embed_links=True,
                    read_message_history=True,
                    manage_messages=True
                ),
                color=discord.Color.teal(),
                mentionable=False,
                reason="Cargo padrão para o bot com permissões do evento PvP"
            )
        except discord.Forbidden:
            logging.warning(f"Permissões insuficientes para criar o cargo em {guild.name}")
            return
        except Exception as e:
            logging.error(f"Erro ao criar o cargo em {guild.name}: {e}")
            return

    bot_member = guild.get_member(bot.user.id)
    if bot_member and cargo not in bot_member.roles:
        try:
            await bot_member.add_roles(cargo, reason="Atribuição automática do cargo Bot KVM")
            logging.info(f"Cargo '{nome_cargo}' atribuído ao bot em {guild.name}.")
        except discord.Forbidden:
            logging.warning(f"Permissões insuficientes para atribuir o cargo em {guild.name}")
        except Exception as e:
            logging.error(f"Erro ao atribuir o cargo em {guild.name}: {e}")

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
