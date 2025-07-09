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

        # Botões organizados em 3 linhas: 5 + 5 + 3
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

        # Botões extras na linha 3
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

        if any(custom_id.startswith(prefix) for prefix in ["classe_", "sair_"]):
            return True

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

            # Remove jogador de outros grupos se estiver
            for g_id, g in grupos_ativos.items():
                if any(j['id'] == user.id for j in g['jogadores']):
                    if g_id != msg_id:
                        g['jogadores'] = [j for j in g['jogadores'] if j['id'] != user.id]
                        canal = bot.get_channel(g['canal_id'])
                        if canal:
                            try:
                                msg_antiga = await canal.fetch_message(g_id)
                                if msg_antiga:
                                    view_antiga = GrupoView(g['grupo'], g['criador_id'], msg_antiga)
                                    linhas_antigas = [f"{CLASSES_EMOJIS[c['classe']]} {c['nome']}" for c in g['jogadores']]
                                    desc_antiga = "\n".join(linhas_antigas) if linhas_antigas else "*Sem jogadores ainda.*"
                                    embed_antiga = discord.Embed(
                                        title=f"PT {g['grupo']}",
                                        description=desc_antiga,
                                        color=0x2B2D31
                                    )
                                    await msg_antiga.edit(embed=embed_antiga, view=view_antiga)
                            except Exception as e:
                                logging.warning(f"Erro ao atualizar mensagem antiga: {e}")

            if len(grupo['jogadores']) >= 5 and all(j['id'] != user.id for j in grupo['jogadores']):
                await interaction.followup.send("Este grupo já atingiu o limite de 5 jogadores.", ephemeral=True)
                return

            entrou = False
            for j in grupo['jogadores']:
                if j['id'] == user.id:
                    j['classe'] = classe
                    entrou = True
                    break

            if not entrou:
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
            try:
                await self.mensagem.edit(embed=embed, view=self)
            except Exception as e:
                logging.warning(f"Falha ao editar mensagem no callback da classe: {e}")
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
        try:
            await self.mensagem.edit(embed=embed, view=self)
        except Exception as e:
            logging.warning(f"Falha ao editar mensagem no sair_callback: {e}")
        await interaction.response.send_message("Você saiu do grupo.", ephemeral=True)

    async def fechar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador pode fechar o grupo.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True
        try:
            await self.mensagem.edit(view=self)
        except Exception as e:
            logging.warning(f"Falha ao editar mensagem no fechar_callback: {e}")
        await interaction.response.send_message("Grupo fechado. Ninguém mais pode entrar.", ephemeral=True)

    async def recriar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador pode recriar o grupo.", ephemeral=True)
            return

        grupo['jogadores'].clear()
        for item in self.children:
            item.disabled = False

        embed = discord.Embed(
            title=f"PT {grupo['grupo']}",
            description="*Sem jogadores ainda.*",
            color=0x2B2D31
        )
        try:
            await self.mensagem.edit(embed=embed, view=self)
        except Exception as e:
            logging.warning(f"Falha ao editar mensagem no recriar_callback: {e}")
        await interaction.response.send_message("Grupo recriado e aberto.", ephemeral=True)

    async def apagar_callback(self, interaction: discord.Interaction):
        msg_id = self.mensagem.id
        grupo = grupos_ativos.get(msg_id)

        if not grupo:
            await interaction.response.send_message("Erro: grupo não encontrado.", ephemeral=True)
            return

        if interaction.user.id != grupo['criador_id']:
            await interaction.response.send_message("Apenas o criador pode apagar o grupo.", ephemeral=True)
            return

        canal = bot.get_channel(grupo['canal_id'])
        if canal:
            try:
                await self.mensagem.delete()
            except Exception as e:
                logging.warning(f"Falha ao apagar mensagem do grupo: {e}")

        grupos_ativos.pop(msg_id, None)
        await interaction.response.send_message("Grupo apagado com sucesso.", ephemeral=True)

@bot.command()
async def criargrupo(ctx, *, arg=None):
    # Sincroniza grupos_ativos limpando grupos fantasmas
    await sincronizar_grupos(ctx.channel.id)

    if not arg:
        await criargrupo_unico(ctx, None)
        return

    try:
        grupos_para_criar = set()
        partes = [p.strip() for p in arg.split(',')]
        for parte in partes:
            if '-' in parte:
                inicio, fim = parte.split('-')
                inicio = int(inicio)
                fim = int(fim)
                if inicio > fim or inicio < 1 or fim > 20:
                    await ctx.send(f"Intervalo inválido: {parte}. Use números entre 1 e 20.")
                    return
                grupos_para_criar.update(range(inicio, fim + 1))
            else:
                num = int(parte)
                if num < 1 or num > 20:
                    await ctx.send(f"Número inválido: {num}. Use números entre 1 e 20.")
                    return
                grupos_para_criar.add(num)

        grupos_para_criar = sorted(grupos_para_criar)

        for grupo_num in grupos_para_criar:
            existe = False
            for g in grupos_ativos.values():
                if g['canal_id'] == ctx.channel.id and g['grupo'] == grupo_num:
                    existe = True
                    await ctx.send(f"Grupo PT {grupo_num} já existe neste canal. Ignorando.")
                    break
            if not existe:
                await criargrupo_unico(ctx, grupo_num)
                await asyncio.sleep(0.2)

        try:
            await ctx.message.delete()
        except:
            pass

    except Exception as e:
        await ctx.send(f"Erro no comando: {e}")

async def criargrupo_unico(ctx, grupo_num=None):
    logging.info(f"Grupos ativos antes de criar: {[ (g['grupo'], g['canal_id']) for g in grupos_ativos.values()]}")
    await sincronizar_grupos(ctx.channel.id)

    for g in grupos_ativos.values():
        if g['canal_id'] == ctx.channel.id and g['grupo'] == grupo_num:
            await ctx.send(f"Grupo PT {grupo_num} já existe neste canal. Ignorando criação.")
            return

    if grupo_num is None:
        numeros_existentes = [g['grupo'] for g in grupos_ativos.values() if g['canal_id'] == ctx.channel.id]
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
    try:
        await msg.edit(view=view)
    except Exception as e:
        logging.warning(f"Falha ao editar mensagem após criação do grupo {grupo_num}: {e}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def limpargrupos(ctx):
    grupos_para_remover = [msg_id for msg_id, g in grupos_ativos.items() if g['canal_id'] == ctx.channel.id]
    for msg_id in grupos_para_remover:
        try:
            msg = await ctx.channel.fetch_message(msg_id)
            await msg.delete()
        except Exception as e:
            logging.warning(f"Não foi possível deletar mensagem {msg_id}: {e}")
        grupos_ativos.pop(msg_id, None)
    await ctx.send("Todos os grupos deste canal foram apagados.", delete_after=10)

@limpargrupos.error
async def limpargrupos_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você precisa da permissão de Gerenciar Mensagens para usar este comando.", delete_after=10)

async def sincronizar_grupos(canal_id):
    msg_ids = [msg_id for msg_id, g in grupos_ativos.items() if g['canal_id'] == canal_id]
    for msg_id in msg_ids:
        try:
            channel = bot.get_channel(canal_id)
            if channel is None:
                logging.warning(f"Canal {canal_id} não encontrado na sincronização.")
                return
            await channel.fetch_message(msg_id)
        except discord.NotFound:
            grupos_ativos.pop(msg_id, None)
            logging.info(f"Removido grupo fantasma com mensagem ID {msg_id} do canal {canal_id}")

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
