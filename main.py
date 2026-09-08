import discord
import os
import uuid
from discord.ext import commands
from logic import DB_Manager
from config import DATABASE, TOKEN
from discord import ui, ButtonStyle, TextStyle

# Modal pencere tanımlama
class TestModal(ui.Modal, title='proje başlık'):
    # Modal pencerede metin alanları tanımlama
    field_1 = ui.TextInput(label='proje adı')
    field_2 = ui.TextInput(label='proje bağlantısı')
    field_3 = ui.TextInput(label='proje açıklaması', style=discord.TextStyle.paragraph)
    field_4 = ui.TextInput(label='proje durumu')
    

    # Modal pencere istendiğinde çağrılan bir yöntem
    async def on_submit(self, interaction: discord.Interaction):
        # Girilen verilerle mesajı güncelleme
        await interaction.message.edit(content=f'proje adı: {self.field_1.value}\n'
                                               f'proje bağlantısı: {self.field_2.value}\n'
                                               f'proje açıklaması: {self.field_3.value}\n'
                                               f'proje durumu: {self.field_4.value}')
                                               
        # Yanıtın daha önce gönderilip gönderilmediğini kontrol etme
        if not interaction.response.is_done():
            # Gecikmeli yanıt için hazırlık yapma
            await interaction.response.defer()
# Buton tanımlama
class TestButton(ui.Button):
    # Belirli özellikler sahip bir butonun başlatılması
    def __init__(self, label="Test etiketi", style=ButtonStyle.blurple, row=0):
        super().__init__(label=label, style=style, row=row)

    # Butona basıldığında çağrılan bir yöntem
    async def callback(self, interaction: discord.Interaction):
        # Kullanıcıya doğrudan mesaj gönderme
        await interaction.user.send("Bir butona bastınız")
        # Butona basılan kanala bir mesaj gönderme
        await interaction.message.channel.send("Bir butona bastınız")
        # Modal pencereyi açma
        await interaction.response.send_modal(TestModal())
        # Basıldıktan sonra butonun stilini değiştirme
        self.style = ButtonStyle.gray

        # Yanıtın daha önce gönderilip gönderilmediğini kontrol etme
        if not interaction.response.is_done():
            # Gecikmeli yanıt için hazırlık yapma
            await interaction.response.defer()

# Buton içeren bir pencere (görünüm) nesnesi tanımlama
class TestView(ui.View):
    # Görünümü başlatma
    def __init__(self):
        super().__init__()
        # Görünüme bir buton ekleme
        self.add_item(TestButton(label="Test etiketi"))
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
manager = DB_Manager(DATABASE)
IMAGE_FOLDER = 'project_images'
manager.create_tables()
manager.default_insert()

@bot.event
async def on_ready():
    print(f'Bot hazır! {bot.user} olarak giriş yapıldı.')
# start : başlatıp kendini tanıtır ve kullanıcıya komutları gösterir
@bot.command(name='start')
async def start_command(ctx):
    await ctx.send("Merhaba! Ben bir proje yöneticisi botuyum.\nProjelerinizi ve onlara dair tüm bilgileri saklamanıza yardımcı olacağım! =)")
    await info(ctx)
    

@bot.command()
async def test(ctx):
    # Bir buton içeren görünüm ile mesaj gönderme
    await ctx.send("Aşağıdaki butona tıklayın:", view=TestView())

# info : kullanıcıya komutları gösterir
@bot.command(name='info')
async def info(ctx):
    await ctx.send("""
Kullanabileceğiniz komutlar şunlardır:

!new_project - yeni bir proje eklemek
!projects - tüm projelerinizi listelemek
!update_projects - proje verilerini güncellemek
!skills - belirli bir projeye beceri eklemek
!delete - bir projeyi silmek

Ayrıca, proje adını yazarak projeyle ilgili tüm bilgilere göz atabilirsiniz!""")
# new_project : kullanıcıdan proje bilgilerini alır ve veritabanına kaydeder
@bot.command(name='new_project')
async def new_project(ctx):
    await test(ctx)
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    name = await bot.wait_for('message', check=check)
    data = [ctx.author.id, name.content]
    await ctx.send("Lütfen projeye ait bağlantıyı gönderin!")
    link = await bot.wait_for('message', check=check)
    data.append(link.content)

    statuses = [x[0] for x in manager.get_statuses()]
    await ctx.send("Lütfen projenin mevcut durumunu girin!", delete_after=60.0)
    await ctx.send("\n".join(statuses), delete_after=60.0)
    
    status = await bot.wait_for('message', check=check)
    if status.content not in statuses:
        await ctx.send("Seçtiğiniz durum listede bulunmuyor. Lütfen tekrar deneyin!", delete_after=60.0)
        return

    status_id = manager.get_status_id(status.content)
    data.append(status_id)

    await ctx.send("Lütfen projeye ait bir resim gönderin!")

    def image_check(msg):
        return (msg.author == ctx.author and msg.channel == ctx.channel
                and msg.attachments)

    image_message = await bot.wait_for('message', check=image_check)
    image = image_message.attachments[0]
    await ctx.send("Resim alındı, kaydediliyor...")

    try:
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        image_filename = f'{uuid.uuid4().hex}_{os.path.basename(image.filename)}'
        image_path = os.path.join(IMAGE_FOLDER, image_filename)
        await image.save(image_path)

        data.append(image_filename)
        manager.insert_project([tuple(data)])
    except Exception as error:
        print(f'Proje resmi kaydedilemedi: {error}')
        await ctx.send("Resim veya proje kaydedilemedi. Bot konsolundaki hata mesajını kontrol edin.")
        return

    await ctx.send("Proje kaydedildi")
# projects : kullanıcının tüm projelerini listeler
@bot.command(name='projects')
async def get_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "\n".join([f"Project name: {x[2]} \nLink: {x[4]}\n" for x in projects])
        await ctx.send(text)
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')
# skills : kullanıcıdan proje ve beceri bilgilerini alır ve veritabanına kaydeder
@bot.command(name='skills')
async def skills(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send('Bir beceri eklemek istediğiniz projeyi seçin')
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin! Beceri eklemek istediğiniz projeyi seçin')
            return

        skills = [x[1] for x in manager.get_skills()]
        await ctx.send('Bir beceri seçin')
        await ctx.send("\n".join(skills))

        skill = await bot.wait_for('message', check=check)
        if skill.content not in skills:
            await ctx.send('Görünüşe göre seçtiğiniz beceri listede yok! Lütfen tekrar deneyin! Bir beceri seçin')
            return

        manager.insert_skill(user_id, project_name.content, skill.content)
        await ctx.send(f'{skill.content} becerisi {project_name.content} projesine eklendi')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')
# delete : kullanıcıdan proje bilgilerini alır ve veritabanından siler
@bot.command(name='delete')
async def delete_project(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Silmek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send('Bu projeye sahip değilsiniz, lütfen tekrar deneyin!')
            return

        project_id = manager.get_project_id(project_name.content, user_id)
        manager.delete_project(user_id, project_id)
        await ctx.send(f'{project_name.content} projesi veri tabanından silindi!')
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')
# update_projects : kullanıcıdan proje ve güncellenecek bilgileri alır ve veritabanında günceller
@bot.command(name='update_projects')
async def update_projects(ctx):
    user_id = ctx.author.id
    projects = manager.get_projects(user_id)
    if projects:
        projects = [x[2] for x in projects]
        await ctx.send("Güncellemek istediğiniz projeyi seçin")
        await ctx.send("\n".join(projects))

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        project_name = await bot.wait_for('message', check=check)
        if project_name.content not in projects:
            await ctx.send("Bir hata oldu! Lütfen güncellemek istediğiniz projeyi tekrar seçin:")
            return

        await ctx.send("Projede neyi değiştirmek istersiniz?")
        attributes = {'Proje adı': 'project_name', 'Açıklama': 'description', 'Proje bağlantısı': 'url', 'Proje durumu': 'status_id'}
        await ctx.send("\n".join(attributes.keys()))

        attribute = await bot.wait_for('message', check=check)
        if attribute.content not in attributes:
            await ctx.send("Hata oluştu! Lütfen tekrar deneyin!")
            return

        if attribute.content == 'Durum':
            statuses = manager.get_statuses()
            await ctx.send("Projeniz için yeni bir durum seçin")
            await ctx.send("\n".join([x[0] for x in statuses]))
            update_info = await bot.wait_for('message', check=check)
            if update_info.content not in [x[0] for x in statuses]:
                await ctx.send("Yanlış durum seçildi, lütfen tekrar deneyin!")
                return
            update_info = manager.get_status_id(update_info.content)
        else:
            await ctx.send(f"{attribute.content} için yeni bir değer girin")
            update_info = await bot.wait_for('message', check=check)
            update_info = update_info.content

        manager.update_projects(attributes[attribute.content], (update_info, project_name.content, user_id))
        await ctx.send("Tüm işlemler tamamlandı! Proje güncellendi!")
    else:
        await ctx.send('Henüz herhangi bir projeniz yok!\nBir tane eklemeyi düşünün! !new_project komutunu kullanabilirsiniz.')

bot.run(TOKEN)