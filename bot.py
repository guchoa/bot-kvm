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
    'bruxo': '🔵',
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
                emoji = discord.PartialEmoji(name=nome, id=id)
            else:
                emoji = emoji_str

            button = discord.ui.Button(
                label=classe.capitalize(),
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)

        self.add_item(discord.ui.Button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id=f"sair_{grupo_numero}"))
        self.add_item(discord.ui.Button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, custom_id=f"fechar_{grupo_numero}"))
        self.add_item(discord.ui.Button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, custom_id=f"recriar_{grupo_numero}"))
        self.add_item(discord.ui.Button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, custom_id=f"apagar_{grupo_numero}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        grupo = grupos_ativos.get(self.mensagem.id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Permitir para todos os botões de classe e sair
        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

        # Outros botões só para o criador
        if user_id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return False

        return True

    def gerar_callback(self, classe):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            grupo = grupos_ativos.get(self.mensagem.id)
            if not grupo:
                await interaction.followup.send("Erro: grupo não encontrado.", ephemeral=True)
                return

            user = interaction.user
            nome = interaction.guild.get_member(user.id).display_name

            # Remove usuário de outras classes para não duplicar
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            grupo['jogadores'].append({'id': user.id, 'nome': nome, 'classe': classe})

            linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
            descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

            embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
            await self.mensagem.edit(embed=embed, view=self)
            await interaction.followup.send(f"Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

    @discord.ui.button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id="dummy_sair")  # dummy custom_id só para o decorator
    async def sair_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        user_id = interaction.user.id
        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]

        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("Você não estava nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(title=f"PT {grupo['grupo']}", description=descricao, color=0x2B2D31)
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    @discord.ui.button(label="🔒 Fechar Grupo", style=discord.ButtonStyle.primary, custom_id="dummy_fechar")
    async def fechar_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await self.mensagem.edit(view=self)
        await interaction.response.send_message(f"O grupo PT {grupo['grupo']} foi fechado para novas inscrições.", ephemeral=True)

    @discord.ui.button(label="♻️ Recriar Grupo", style=discord.ButtonStyle.secondary, custom_id="dummy_recriar")
    async def recriar_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        novo_embed = discord.Embed(title=f"PT {grupo['grupo']}", description="*Sem jogadores ainda.*", color=0x2B2D31)
        nova_view = GrupoView(grupo_numero=grupo['grupo'], criador_id=interaction.user.id)
        nova_msg = await self.mensagem.channel.send(embed=novo_embed, view=nova_view)
        nova_view.mensagem = nova_msg

        grupos_ativos[nova_msg.id] = {
            'grupo': grupo['grupo'],
            'jogadores': [],
            'criador_id': interaction.user.id,
            'mensagem': nova_msg
        }
        await interaction.response.send_message("Grupo recriado com sucesso.", ephemeral=True)

    @discord.ui.button(label="🗑️ Apagar Grupo", style=discord.ButtonStyle.danger, custom_id="dummy_apagar")
    async def apagar_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        grupo = grupos_ativos.get(self.mensagem.id)
        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        await self.mensagem.delete()
        grupos_ativos.pop(self.mensagem.id, None)
        await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        logging.info(f"Comando !criargrupo recebido de {ctx.author}")

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

        try:
            await ctx.message.delete()
        except Exception as e:
            logging.warning(f"Não foi possível deletar a mensagem de comando: {e}")

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
            logging.info(f"Grupo PT {numero} criado.")
            await asyncio.sleep(1)

    except Exception as e:
        logging.error(f"Erro inesperado ao criar grupo: {e}")
        await ctx.send("❌ Ocorreu um erro ao criar o grupo. Verifique os logs.")

@bot.event
async def on_ready():
    logging.info(f'Bot está online! Logado como {bot.user} (ID: {bot.user.id})')
    for guild in bot.guilds:
        await garantir_cargo_bot(guild)

@bot.event
async def on_guild_join(guild):
    await garantir_cargo_bot(guild)

async def garantir_cargo_bot(guild):
    nome_cargo = "Bot KVM"
    cargo = discord.utils.get(guild.roles, name=nome_cargo)

    if not cargo:
        logging.info(f"Criando cargo '{nome_cargo}' em {guild.name}...")
        try:
            cargo = await guild.create_role(
                name=nome_cargo,
                permissions=discord.Permissions.all(),
                color=discord.Color.teal(),
                mentionable=False,
                reason="Cargo padrão para o bot com todas permissões necessárias"
            )
            logging.info(f"Cargo '{nome_cargo}' criado com sucesso em {guild.name}.")
        except discord.Forbidden:
            logging.warning(f"Permissões insuficientes para criar o cargo em {guild.name}")
            return
        except Exception as e:
            logging.error(f"Erro ao criar o cargo em {guild.name}: {e}")
            return

    bot_member = guild.get_member(bot.user.id)
    if bot_member:
        if cargo not in bot_member.roles:
            if guild.me.top_role.position > cargo.position:
                try:
                    await bot_member.add_roles(cargo, reason="Atribuição automática do cargo Bot KVM")
                    logging.info(f"Cargo '{nome_cargo}' atribuído ao bot em {guild.name}.")
                except discord.Forbidden:
                    logging.warning(f"Permissões insuficientes para atribuir o cargo em {guild.name}")
                except Exception as e:
                    logging.error(f"Erro ao atribuir o cargo em {guild.name}: {e}")
            else:
                logging.warning(f"Cargo '{nome_cargo}' está acima do cargo do bot em {guild.name}. Ajuste a hierarquia manualmente.")
        else:
            logging.info(f"Bot já possui o cargo '{nome_cargo}' em {guild.name}.")
    else:
        logging.warning(f"Bot não encontrado no servidor {guild.name}.")

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
