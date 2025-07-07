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

        # Adiciona botões das classes (máximo 5 por linha)
        count = 0
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
                custom_id=f"classe_{classe}_{grupo_numero}"
            )
            button.callback = self.gerar_callback(classe)
            self.add_item(button)
            count += 1

            # Discord limita 5 botões por linha automaticamente, então não precisa se preocupar com isso manualmente

        # Agora adiciona os botões de ação — só 1 vez, sem duplicação:
        self.add_item(discord.ui.Button(
            label="❌ Sair do Grupo",
            style=discord.ButtonStyle.danger,
            custom_id=f"sair_{grupo_numero}"
        ))

        self.add_item(discord.ui.Button(
            label="🔒 Fechar Grupo",
            style=discord.ButtonStyle.primary,
            custom_id=f"fechar_{grupo_numero}"
        ))

        self.add_item(discord.ui.Button(
            label="♻️ Recriar Grupo",
            style=discord.ButtonStyle.secondary,
            custom_id=f"recriar_{grupo_numero}"
        ))

        self.add_item(discord.ui.Button(
            label="🗑️ Apagar Grupo",
            style=discord.ButtonStyle.danger,
            custom_id=f"apagar_{grupo_numero}"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("❌ Erro: grupo não encontrado.", ephemeral=True)
            return False

        # Permitir para TODOS os membros os botões de classe e sair
        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

        # Botões de controle (fechar, recriar, apagar) só para o criador
        if user_id != grupo['criador_id']:
            await interaction.response.send_message("❌ Apenas o criador do grupo pode usar este botão.", ephemeral=True)
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
                await interaction.followup.send("❌ Erro: grupo não encontrado.", ephemeral=True)
                return

            # Remove usuário de qualquer classe antes de adicionar (pra evitar duplicata)
            grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user.id]

            # Limite de 5 jogadores
            if len(grupo['jogadores']) >= 5:
                await interaction.followup.send("❌ Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
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
            await interaction.followup.send(f"✅ Você entrou como **{classe.capitalize()}**!", ephemeral=True)

        return callback

    async def on_error(self, error: Exception, item, interaction: discord.Interaction):
        logging.error(f"Erro na interação: {error}")
        await interaction.response.send_message("❌ Ocorreu um erro na interação.", ephemeral=True)

    @discord.ui.button(label="❌ Sair do Grupo", style=discord.ButtonStyle.danger, custom_id="dummy_sair")  # dummy para evitar erro
    async def sair_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Nota: esse botão "dummy" não será mostrado, pois adicionamos manualmente o real no __init__
        pass

    async def sair_callback_real(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("❌ Erro: grupo não encontrado.", ephemeral=True)
            return

        jogadores_antes = len(grupo['jogadores'])
        grupo['jogadores'] = [j for j in grupo['jogadores'] if j['id'] != user_id]

        if len(grupo['jogadores']) == jogadores_antes:
            await interaction.response.send_message("❌ Você não estava nesse grupo.", ephemeral=True)
            return

        linhas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in grupo['jogadores']]
        descricao = "\n".join(linhas) if linhas else "*Sem jogadores ainda.*"

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description=descricao,
            color=0x2B2D31
        )
        await self.mensagem.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você saiu do grupo.", ephemeral=True)

    # Callbacks para botões de controle: fechar, recriar, apagar
    async def fechar_callback_real(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("❌ Erro: grupo não encontrado.", ephemeral=True)
            return

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("❌ Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        await self.mensagem.edit(view=self)
        await interaction.response.send_message(f"🔒 O grupo PT {grupo['grupo']} foi fechado para novas inscrições.", ephemeral=True)

    async def recriar_callback_real(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("❌ Erro: grupo não encontrado.", ephemeral=True)
            return

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("❌ Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

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
        await interaction.response.send_message("♻️ Grupo recriado com sucesso.", ephemeral=True)

    async def apagar_callback_real(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)
        user_id = interaction.user.id

        if not grupo:
            await interaction.response.send_message("❌ Erro: grupo não encontrado.", ephemeral=True)
            return

        if user_id != grupo['criador_id']:
            await interaction.response.send_message("❌ Apenas o criador do grupo pode usar este botão.", ephemeral=True)
            return

        await self.mensagem.delete()
        grupos_ativos.pop(msg_id, None)
        await interaction.response.send_message("🗑️ Grupo apagado com sucesso.", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """
    Roteia as interações para os callbacks corretos, porque
    os botões foram criados manualmente (não com decorator),
    então precisamos lidar com eles aqui.
    """
    if not interaction.data or 'custom_id' not in interaction.data:
        return

    custom_id = interaction.data['custom_id']

    # Buscar a view relacionada (mensagem)
    grupo = grupos_ativos.get(interaction.message.id)
    if not grupo:
        await interaction.response.send_message("❌ Grupo não encontrado.", ephemeral=True)
        return

    view = None
    # Encontrar a view da mensagem
    if hasattr(interaction.message, "components") and interaction.message.components:
        # Criamos a view? Sim, então:
        for child in interaction.message.components:
            pass  # só para garantir componente existe

    # Criar uma instância da view para gerenciar callbacks
    # IMPORTANTE: Passar criador_id e mensagem para acessar grupo e permissões
    view = GrupoView(grupo_numero=grupo['grupo'], criador_id=grupo['criador_id'], mensagem=interaction.message)

    # Disparar o callback correto pelo custom_id
    # Classes
    if custom_id.startswith("classe_"):
        classe = custom_id.split("_")[1]
        await view.gerar_callback(classe)(interaction)
        return

    # Sair
    if custom_id.startswith("sair_"):
        await view.sair_callback_real(interaction)
        return

    # Fechar
    if custom_id.startswith("fechar_"):
        await view.fechar_callback_real(interaction)
        return

    # Recriar
    if custom_id.startswith("recriar_"):
        await view.recriar_callback_real(interaction)
        return

    # Apagar
    if custom_id.startswith("apagar_"):
        await view.apagar_callback_real(interaction)
        return

@bot.command(name='criargrupo')
async def criar_grupo(ctx, intervalo: str):
    try:
        logging.info(f"Comando !criargrupo recebido de {ctx.author}")

        if '-' in intervalo:
            inicio, fim = map(int, intervalo.split('-'))
            if not (1 <= inicio <= 20 and 1 <= fim <= 20) or inicio > fim:
                await ctx.send("❌ Intervalo inválido. Use números entre 1 e 20, como !criargrupo 1-5.")
                return
            numeros = range(inicio, fim + 1)
        else:
            numero = int(intervalo)
            if not (1 <= numero <= 20):
                await ctx.send("❌ Número de PT inválido. Use um número entre 1 e 20.")
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
