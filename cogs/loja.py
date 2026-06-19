import discord
from discord.ext import commands
import aiosqlite

class ModalCriarHabilidade(discord.ui.Modal):
    def __init__(self, aluno_id):
        super().__init__(title="Criar Nova Habilidade")
        self.aluno_id = aluno_id
        
        self.add_item(discord.ui.InputText(label="Nome da Habilidade", placeholder="Ex: Bola de Fogo"))
        self.add_item(discord.ui.InputText(label="Descrição e Efeitos", style=discord.InputTextStyle.paragraph))

    async def callback(self, interaction: discord.Interaction):
        nome_hab = self.children[0].value.strip()
        desc_hab = self.children[1].value.strip()
        
        async with aiosqlite.connect('escola.db') as db:
            await db.execute("INSERT OR IGNORE INTO biblioteca (nome, descricao, tipo, custo, custo_folego) VALUES (?, ?, ?, ?, ?)", 
                          (nome_hab, desc_hab, "Habilidade", 0, 0))
            
            async with db.execute("SELECT id FROM biblioteca WHERE nome = ?", (nome_hab,)) as cursor:
                hid = (await cursor.fetchone())[0]
            
            await db.execute("INSERT INTO posses (aluno_id, conhecimento_id) VALUES (?, ?)", (self.aluno_id, hid))
            await db.execute("UPDATE alunos SET fichas_habilidade = fichas_habilidade - 1 WHERE id = ?", (self.aluno_id,))
            
            await db.commit()
        
        await interaction.response.send_message(f"⚔️ **{nome_hab}** criada com sucesso! Verifique sua ficha.", ephemeral=True)

class ViewCompraAptidao(discord.ui.View):
    def __init__(self, aptidoes_lista, aluno_data):
        super().__init__(timeout=120)
        self.aluno_id = aluno_data[0]
        self.fichas_apt = aluno_data[1]
        self.estrelas = aluno_data[2]
        
        options = [discord.SelectOption(label=a[0], description=f"Custo: {a[1]}⭐") for a in aptidoes_lista]
        
        self.select = discord.ui.Select(placeholder="Selecione a Aptidão...", options=options)
        self.select.callback = self.comprar_aptidao
        self.add_item(self.select)

    async def comprar_aptidao(self, interaction: discord.Interaction):
        nome_apt = self.select.values[0]
        
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute("SELECT id, custo FROM biblioteca WHERE nome = ? AND tipo = 'Aptidão'", (nome_apt,)) as cursor:
                apt = await cursor.fetchone()
            
            async with db.execute("SELECT 1 FROM posses WHERE aluno_id = ? AND conhecimento_id = ?", (self.aluno_id, apt[0])) as cursor:
                if await cursor.fetchone():
                    return await interaction.response.send_message("❌ Você já possui esta aptidão!", ephemeral=True)
                    
            if self.fichas_apt > 0:
                await db.execute("UPDATE alunos SET fichas_aptidao = fichas_aptidao - 1 WHERE id = ?", (self.aluno_id,))
                metodo_pago = "🎫 1 Ficha de Aptidão"
            elif self.estrelas >= apt[1]:
                await db.execute("UPDATE alunos SET estrelas = estrelas - ? WHERE id = ?", (apt[1], self.aluno_id))
                metodo_pago = f"⭐ {apt[1]} Estrelas"
            else:
                return await interaction.response.send_message(f"❌ Você não tem recursos suficientes. Custa {apt[1]}⭐ ou 1 Ficha.", ephemeral=True)
                
            await db.execute("INSERT INTO posses (aluno_id, conhecimento_id) VALUES (?, ?)", (self.aluno_id, apt[0]))
            await db.commit()
        
        await interaction.response.send_message(f"🌿 Você comprou **{nome_apt}** usando {metodo_pago}!", ephemeral=True)
class ViewCompraAtributo(discord.ui.View):
    def __init__(self, aluno_data):
        super().__init__(timeout=120)
        self.aluno_id = aluno_data[0]
        self.estrelas = aluno_data[1]
        self.custo_atributo = 10
        
        options = [
            discord.SelectOption(label="Corpo", emoji="💪"),
            discord.SelectOption(label="Mente", emoji="🧠"),
            discord.SelectOption(label="Coração", emoji="❤️")
        ]
        self.select = discord.ui.Select(placeholder=f"Evoluir Atributo ({self.custo_atributo}⭐)", options=options)
        self.select.callback = self.comprar_atributo
        self.add_item(self.select)

    async def comprar_atributo(self, interaction: discord.Interaction):
        atributo = self.select.values[0].lower()
        
        if self.estrelas < self.custo_atributo:
            return await interaction.response.send_message(f"❌ Você precisa de **{self.custo_atributo}⭐** para subir um atributo.", ephemeral=True)
            
        async with aiosqlite.connect('escola.db') as db:
            await db.execute(f"UPDATE alunos SET estrelas = estrelas - ?, {atributo} = {atributo} + 1 WHERE id = ?", 
                          (self.custo_atributo, self.aluno_id))
            
            async with db.execute("SELECT corpo, mente, coracao, atributo_folego, folego_treino FROM alunos WHERE id = ?", (self.aluno_id,)) as cursor:
                c, m, cora, attr_f, f_treino = await cursor.fetchone()
            
            valor_base = c if attr_f == 'corpo' else (m if attr_f == 'mente' else cora)
            novo_folego_max = 100 + (valor_base * 10) + f_treino
            
            await db.execute("UPDATE alunos SET folego_atual = ? WHERE id = ?", (novo_folego_max, self.aluno_id))
            await db.commit()
        
        await interaction.response.send_message(f"Você gastou {self.custo_atributo}⭐ e ganhou **+1 em {atributo.capitalize()}**!", ephemeral=True)

async def abrir_loja_interface(interaction: discord.Interaction, tipo: str, aluno_data: tuple, is_edit: bool = False):
    aluno_id, nome_char, fichas_apt, estrelas, fichas_hab = aluno_data

    if tipo == "Habilidades":
        if fichas_hab <= 0:
            msg = f"❌ **{nome_char}** não tem **🎫 Fichas de Habilidade**."
            if is_edit: return await interaction.response.edit_message(content=msg, view=None)
            else: return await interaction.response.send_message(msg, ephemeral=True)
        
        await interaction.response.send_modal(ModalCriarHabilidade(aluno_id))
        
    elif tipo == "Aptidões":
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute("SELECT nome, custo FROM biblioteca WHERE tipo = 'Aptidão'") as cursor:
                aptidoes = await cursor.fetchall()
        
        if not aptidoes:
            msg = "❌ Nenhuma aptidão cadastrada na loja ainda."
            if is_edit: return await interaction.response.edit_message(content=msg, view=None)
            else: return await interaction.response.send_message(msg, ephemeral=True)
            
        view_apt = ViewCompraAptidao(aptidoes, (aluno_id, fichas_apt, estrelas))
        content = f"🌿 **Loja de Aptidões ({nome_char})**\nEscolha com sabedoria. Você pode pagar com Estrelas ou Fichas de Aptidão."
        
        if is_edit: await interaction.response.edit_message(content=content, view=view_apt)
        else: await interaction.response.send_message(content, view=view_apt, ephemeral=True)

    elif tipo == "Atributos":
        view_attr = ViewCompraAtributo((aluno_id, estrelas))
        content = f"💪 **Treinamento de Atributos ({nome_char})**\nEscolha qual atributo deseja evoluir."
        
        if is_edit: await interaction.response.edit_message(content=content, view=view_attr)
        else: await interaction.response.send_message(content, view=view_attr, ephemeral=True)

class ViewSelecionarPersonagem(discord.ui.View):
    def __init__(self, tipo, personagens):
        super().__init__(timeout=120)
        self.tipo = tipo
        # Guarda os dados do aluno num dicionário pra recuperar na hora do clique
        self.personagens_dict = {str(p[0]): p for p in personagens}
        
        options = [
            discord.SelectOption(
                label=p[1], 
                description=f"⭐ {p[3]} | 🎫 Hab: {p[4]} | 🌿 Apt: {p[2]}", 
                value=str(p[0]),
                emoji="👤"
            )
            for p in personagens
        ]
        self.select = discord.ui.Select(placeholder="Selecione quem fará a compra...", options=options)
        self.select.callback = self.selecionar
        self.add_item(self.select)

    async def selecionar(self, interaction: discord.Interaction):
        aluno_id = self.select.values[0]
        aluno_data = self.personagens_dict[aluno_id]
        # is_edit=True avisa o bot para substituir a mensagem do menu pela loja
        await abrir_loja_interface(interaction, self.tipo, aluno_data, is_edit=True)

class ViewBotaoLoja(discord.ui.View):
    def __init__(self, tipo):
        super().__init__(timeout=None) 
        self.tipo = tipo

        btn = discord.ui.Button(
            label=f"🛒 Acessar {tipo}",
            style=discord.ButtonStyle.success,
            custom_id=f"loja_btn_{tipo}" 
        )
        btn.callback = self.clique_loja
        self.add_item(btn)

    async def clique_loja(self, interaction: discord.Interaction):
        async with aiosqlite.connect('escola.db') as db:
            async with db.execute("SELECT id, nome_personagem, fichas_aptidao, estrelas, fichas_habilidade FROM alunos WHERE owner_id = ?", (interaction.user.id,)) as cursor:
                alunos = await cursor.fetchall()
        
        if not alunos:
            return await interaction.response.send_message("❌ Você não possui uma ficha registrada para acessar a loja.", ephemeral=True)
            
        if len(alunos) == 1:
            await abrir_loja_interface(interaction, self.tipo, alunos[0], is_edit=False)
        else:
            view_selecao = ViewSelecionarPersonagem(self.tipo, alunos)
            await interaction.response.send_message("👥 **Múltiplos Personagens:** Selecione quem vai acessar o balcão.", view=view_selecao, ephemeral=True)

class ModalSetupLoja(discord.ui.Modal):
    def __init__(self, tipo):
        super().__init__(title=f"Configurar Loja: {tipo}")
        self.tipo = tipo
        
        self.add_item(discord.ui.InputText(label="Texto da Mensagem", style=discord.InputTextStyle.paragraph, placeholder="Bem-vindos à loja! Aqui você pode..."))
        self.add_item(discord.ui.InputText(label="URL da Imagem (Opcional)", required=False, placeholder="https://link-da-imagem.png"))

    async def callback(self, interaction: discord.Interaction):
        texto = self.children[0].value
        url_imagem = self.children[1].value
        
        mensagem_final = f"{texto}"
        view = ViewBotaoLoja(self.tipo)
        if url_imagem:
            embed_imagem = discord.Embed()
            embed_imagem.set_image(url=url_imagem)
            await interaction.channel.send(content=mensagem_final, embed=embed_imagem, view=view)
        else:
            await interaction.channel.send(content=mensagem_final, view=view)
            
        await interaction.response.send_message("✅ Painel da loja criado com sucesso!", ephemeral=True)

class Loja(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ViewBotaoLoja("Atributos"))
        self.bot.add_view(ViewBotaoLoja("Habilidades"))
        self.bot.add_view(ViewBotaoLoja("Aptidões"))

    @discord.slash_command(name="setup_loja", description="[ADM] Instala o painel de compras em um canal")
    @commands.has_permissions(administrator=True)
    async def setup_loja(
        self, ctx, 
        tipo: str = discord.Option(str, choices=["Atributos", "Habilidades", "Aptidões"], description="Qual balcão deseja instalar aqui?")
    ):
        await ctx.send_modal(ModalSetupLoja(tipo))

def setup(bot):
    bot.add_cog(Loja(bot))