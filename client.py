
# 📦 ІМПОРТ НЕОБХІДНИХ БІБЛІОТЕК (Інструменти, які нам допомагають):
import base64     # Допомагає кодувати картинки у текстовий рядок, щоб відправляти їх мережею
import io         # Працює з вхідними та вихідними потоками даних у пам'яті
import os         # Допомагає шукати файли на нашому комп'ютері (наприклад, де лежать картинки)
import threading  # Дозволяє виконувати кілька завдань одночасно (наприклад, чекати нових повідомлень у фоні)
from socket import socket, AF_INET, SOCK_STREAM  # Наша "телефонна трубка" для зв'язку з сервером

# Бібліотека CustomTkinter — створює сучасні та красиві кнопки, поля вводу та вікна:
from customtkinter import CTk, CTkFrame, CTkScrollableFrame, CTkEntry, CTkButton, CTkLabel, CTkImage, END
# Допоміжне віконце для вибору файлу з картинкою на комп'ютері:
from tkinter import filedialog
# Бібліотека PIL (Pillow) — малює та обробляє зображення (обрізає у кружечки, змінює розмір):
from PIL import Image, ImageDraw, ImageFont


# ==============================================================================
# 🏠 ГОЛОВНИЙ КЛАС ВІКНА (MainWindow)

class MainWindow(CTk):
    def __init__(self):
        """Конструктор вікна: викликається автоматично при запуску програми."""
        super().__init__()

        # 📏 1. НАЛАШТУВАННЯ РОЗМІРУ ТА ЗАГОЛОВКА ВІКНА
        self.geometry('800x600')  # Початковий розмір вікна: ширина 800 пікселів, висота 600 пікселів
        self.title("Logi Talk Pro")  # Назва програми зверху вікна
        self.minsize(300, 250)      # Мінімально можливий розмір вікна, щоб воно не зламалося

        # 📋 2. ЗМІННІ ТА АТРИБУТИ (Тут ми зберігаємо стан нашої програми)
        self.username = ""                 # Ім'я користувача (за замовчуванням порожнє)
        self.user_avatar = None            # Головний аватар користувача для меню (60x60 пікселів)
        self.user_avatar_chat = None       # Аватар користувача для повідомлень у чаті (40x40)
        self.system_avatar_chat = None     # Аватар для системних сповіщень (40x40)
        self.user_avatars_cache = {}       # "Сховище" (кеш) аватарок інших друзів у чаті
        self.menu_width = 30               # Початкова ширина бічного меню в пікселях
        self.label = None                  # Підпис з іменем у меню
        self.entry = None                  # Поле для введення нового імені в меню
        self.save_button = None            # Кнопка збереження імені в меню
        self.sock: socket | None = None    # Об'єкт мережевого з'єднання (сокет)

        # 🖼️ 3. ЗАВАНТАЖЕННЯ КАРТИНОК-АВАТАРОК
        self.load_main_avatar()
        self.load_chat_avatars()

        # 🧱 4. БУДУЄМО СТРУКТУРУ ІНТЕРФЕЙСУ (Дизайн вікна)
        
        # Бічне меню (зліва) — тут зберігається профіль користувача
        self.menu_frame = CTkFrame(self, width=self.menu_width)
        self.menu_frame.place(x=0, y=0, relheight=1)  # Займає всю висоту вікна
        self.menu_frame.pack_propagate(False)         # Не даємо віджетам змінювати розмір меню

        # Головна область (справа) — для списку повідомлень та поля вводу
        self.main_frame = CTkFrame(self, fg_color="transparent")
        self.main_frame.place(x=self.menu_width, y=0, relheight=1)

        # Слідкуємо за тим, коли користувач змінює розмір вікна мишкою
        self.bind("<Configure>", self.on_resize)

        # Нижній блок для введення повідомлення
        self.input_frame = CTkFrame(self.main_frame, height=45, fg_color="transparent")
        self.input_frame.pack(side='bottom', fill='x', padx=5, pady=5)

        # Центральна область чату зі смугою прокрутки (ScrollableFrame)
        self.chat_field = CTkScrollableFrame(self.main_frame)
        self.chat_field.pack(side='top', expand=True, fill='both', padx=5, pady=(5, 0))

        # ⌨️ 5. ЕЛЕМЕНТИ УПРАВЛІННЯ (Поле вводу та кнопки)
        self.message_entry = CTkEntry(self.input_frame, placeholder_text='Введіть повідомлення:')
        self.send_button = CTkButton(self.input_frame, text='>', width=50, command=self.send_message)
        self.open_img_button = CTkButton(self.input_frame, text='📂', width=50, command=self.open_image)

        # Розставляємо елементи в нижній панелі
        self.send_button.pack(side='right', padx=(0, 0), pady=0, fill='y')
        self.open_img_button.pack(side='right', padx=5, pady=0, fill='y')
        self.message_entry.pack(expand=True, fill='both', pady=0)

        # Кнопка відкриття/закриття бічного меню (маленький трикутник зверху)
        self.is_show_menu = False  # Чи відкрите меню зараз?
        self.is_animating = False  # Чи рухається меню прямо зараз? (щоб уникнути глюків)
        self.btn = CTkButton(self, text='▶️', command=self.toggle_show_menu, width=30, height=30)
        self.btn.place(x=0, y=0)
        self.btn.lift()  # Піднімаємо кнопку на найвищий шар, щоб її завжди було видно

        # 💬 6. ПРИВІТАЛЬНЕ ПОВІДОМЛЕННЯ
        self.add_message("Ласкаво просимо до чату!", author="SYSTEM")

        # 🔌 7. ПІДКЛЮЧЕННЯ ДО СЕРВЕРА (Мережа)
        try:
            # Створюємо мережеву "трубку" (TCP socket)
            sock = socket(AF_INET, SOCK_STREAM)
            # Намагаємося подзвонити серверу за адресою localhost (наш комп'ютер) та портом 8080
            sock.connect(('localhost', 8080))
            
            # Відправляємо привітальну команду серверу
            hello = f"TEXT@{self.username}@[SYSTEM] {self.username} приєднався(лась) до чату!\n"
            sock.send(hello.encode('utf-8'))
            self.sock = sock

            # Запускаємо окремий потік (Thread), який слухатиме відповіді сервера у фоні
            threading.Thread(target=self.recv_message, daemon=True).start()
        except Exception as e:
            # Якщо сервер вимкнений або сталася помилка:
            print(f"Не вдалося підключитися до сервера: {e}")
            self.sock = None

    # ==========================================================================
    # 🖼️ ФУНКЦІЇ ДЛЯ РОБОТИ З КАРТИНКАМИ ТА АВАТАРКАМИ
    # ==========================================================================
    def load_main_avatar(self):
        """Шукає на диску та завантажує великий круглий аватар користувача для меню."""
        try:
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user-avatar.png")
            self.user_avatar = self.create_circular_avatar(image_path, (60, 60))
        except Exception as e:
            print(f"Помилка завантаження головного аватара: {e}")
            # Якщо файлу немає, малюємо дефолтний кружечок із літерою 'U'
            self.user_avatar = self.create_circular_avatar(None, (60, 60), "U")

    def load_chat_avatars(self):
        """Завантажує малі аватарки (40x40) для повідомлень у чаті."""
        try:
            user_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user-avatar.png")
            self.user_avatar_chat = self.create_circular_avatar(user_image_path, (40, 40))
        except Exception as e:
            print(f"Помилка завантаження аватара користувача для чату: {e}")
            self.user_avatar_chat = self.create_circular_avatar(None, (40, 40), "U")

        try:
            system_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system-avatar.png")
            self.system_avatar_chat = self.create_circular_avatar(system_image_path, (40, 40))
        except Exception as e:
            print(f"Помилка завантаження аватара системи для чату: {e}")
            self.system_avatar_chat = self.create_circular_avatar(None, (40, 40), "S")

    @staticmethod
    def create_circular_avatar(image_path, size, initial='?'):
        """Магія PIL: обрізає будь-яку квадратну картинку у гарний круглий аватар."""
        if image_path and os.path.exists(image_path):
            img = Image.open(image_path).convert("RGBA")
            img = img.resize((size[0], size[1]), Image.Resampling.LANCZOS)
        else:
            # Малюємо новий круг за допомогою цифрового пензля ImageDraw:
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse((0, 0, size[0], size[1]), fill=(0, 0, 0, 255))
            try:
                font = ImageFont.truetype("arial.ttf", int(size[1] * 0.6))
            except IOError:
                font = ImageFont.load_default()
            draw.text((size[0] // 2, size[1] // 2), initial, anchor="mm", fill=(255, 255, 255, 255), font=font)

        # Створюємо круглу маску трафарету
        mask = Image.new('L', (size[0], size[1]), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)

        # Накладаємо маску на картинку
        circular_img = Image.new("RGBA", (size[0], size[1]), (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)

        # Перетворюємо оброблене зображення у формат, зрозумілий CustomTkinter
        return CTkImage(light_image=circular_img, dark_image=circular_img, size=size)

    # ==========================================================================
    # 🎬 АНІМАЦІЯ БІЧНОГО МЕНЮ (Плавне розгортання та згортання)
    # ==========================================================================
    def toggle_show_menu(self):
        """Перемикає стан меню (відкрити/закрити) при натисканні на кнопку-стрілочку."""
        if self.is_animating:
            return  # Якщо анімація вже йде — не реагуємо на повторні кліки

        self.is_animating = True  # Блокуємо повторні кліки

        if self.is_show_menu:
            # ЛОГІКА ЗАКРИТТЯ:
            self.is_show_menu = False
            self.btn.configure(text='▶️')
            # Видаляємо всі кнопки з меню перед його закриттям
            for widget in self.menu_frame.winfo_children():
                widget.destroy()
            self.animate_close_menu()
        else:
            # ЛОГІКА ВІДКРИТТЯ:
            self.is_show_menu = True
            self.btn.configure(text='◀️')
            self.animate_open_menu()

    def on_resize(self, _event=None):
        """Підганяє розмір головної панелі чату, коли вікно змінює свій розмір."""
        if not hasattr(self, 'menu_width') or self.winfo_width() <= 1:
            return
        main_width = self.winfo_width() - self.menu_width
        self.main_frame.place_configure(width=main_width)

    def animate_open_menu(self):
        """Плавні кроки розгортання меню до ширини 200 пікселів."""
        target_width = 200
        if self.menu_width < target_width:
            self.menu_width = min(self.menu_width + 20, target_width)
            self.menu_frame.place_configure(width=self.menu_width)
            main_width = self.winfo_width() - self.menu_width
            self.main_frame.place_configure(x=self.menu_width, width=main_width)
            # Викликаємо цю ж функцію через 10 мілісекунд для створення ефекту руху
            self.after(10, self.animate_open_menu)
        else:
            self.menu_width = target_width
            self.menu_frame.place_configure(width=self.menu_width)
            self.on_resize()
            self.is_animating = False
            self.create_menu_widgets()  # Додаємо елементи профілю після відкриття

    def animate_close_menu(self):
        """Плавні кроки згортання меню до початкової ширини 30 пікселів."""
        target_width = 30
        if self.menu_width > target_width:
            self.menu_width = max(self.menu_width - 20, target_width)
            self.menu_frame.place_configure(width=self.menu_width)
            main_width = self.winfo_width() - self.menu_width
            self.main_frame.place_configure(x=self.menu_width, width=main_width)
            self.after(10, self.animate_close_menu)
        else:
            self.menu_width = target_width
            self.menu_frame.place_configure(width=self.menu_width)
            self.on_resize()
            self.is_animating = False

    def create_menu_widgets(self):
        """Створює віджети профілю (аватар, поле для нікнейму, кнопку збереження)."""
        if self.user_avatar:
            avatar_label = CTkLabel(self.menu_frame, text="", image=self.user_avatar)
            avatar_label.place(relx=0.5, y=50, anchor="center")

        self.label = CTkLabel(self.menu_frame, text='Імʼя')
        self.label.place(relx=0.5, y=95, anchor="center")

        self.entry = CTkEntry(self.menu_frame, placeholder_text="Ваш нік...")
        self.entry.place(relx=0.5, y=130, relwidth=0.8, anchor="center")

        self.save_button = CTkButton(self.menu_frame, text="Зберегти", command=self.save_name)
        self.save_button.place(relx=0.5, y=175, relwidth=0.8, anchor="center")

    def save_name(self):
        """Зберігає новий нікнейм, який користувач ввів у полі."""
        if self.entry:
            new_name = self.entry.get().strip()
            if new_name:
                self.username = new_name
                self.add_message(f"Нік змінено на: {self.username}", author="SYSTEM")

    def get_chat_avatar(self, author):
        """Повертає відповідну аватарку залежно від того, хто написав повідомлення."""
        if author == self.username:
            return self.user_avatar_chat
        if author == "SYSTEM":
            return self.system_avatar_chat

        # Якщо пише новий співрозмовник — створюємо для нього аватарку з його першої літери
        if author not in self.user_avatars_cache:
            initial = author[0].upper() if author else '?'
            self.user_avatars_cache[author] = self.create_circular_avatar(None, (40, 40), initial)

        return self.user_avatars_cache[author]

    # ==========================================================================
    # 💬 ВІДОБРАЖЕННЯ ТА ВІДПРАВЛЕННЯ ПОВІДОМЛЕНЬ
    # ==========================================================================
    def add_message(self, message, img=None, author=None):
        """Створює красивий "хмарковий" блок повідомлення з аватаркою та текстом у чаті."""
        if author is None:
            author = self.username

        avatar_img = self.get_chat_avatar(author)

        align_frame = CTkFrame(self.chat_field, fg_color="transparent")
        msg_container = CTkFrame(align_frame, fg_color="transparent")

        avatar_label = CTkLabel(msg_container, text="", image=avatar_img)
        text_container = CTkFrame(msg_container, fg_color='#4a4a4a', corner_radius=10)

        # Якщо це наші повідомлення — вирівнюємо їх ПРАВОРУЧ, якщо чужі — ЛІВОРУЧ:
        if author == self.username:
            align_frame.pack(fill='x', padx=10, pady=5)
            msg_container.pack(side='right')
            avatar_label.pack(side='right', padx=(10, 0))
            text_container.pack(side='right')
        else:
            align_frame.pack(fill='x', padx=10, pady=5)
            msg_container.pack(side='left')
            avatar_label.pack(side='left', padx=(0, 10))
            text_container.pack(side='left')

        # Заголовок з іменем автора
        if author == "SYSTEM":
            author_label = CTkLabel(text_container, text="System", text_color='gray70', font=('Arial', 12, 'bold'))
            author_label.pack(anchor='w', padx=10, pady=(5, 0))
        else:
            author_label = CTkLabel(text_container, text=author, text_color='cyan', font=('Arial', 12, 'bold'))
            author_label.pack(anchor='w', padx=10, pady=(5, 0))

        # Текст повідомлення або картинка
        msg_label = CTkLabel(text_container, text=message, text_color='white', justify='left', image=img,
                             compound='top', wraplength=400)
        msg_label.pack(anchor='w', padx=10, pady=5)

    def send_message(self):
        """Бере текст з поля вводу та надсилає його через мережу на сервер."""
        message = self.message_entry.get()
        if message and self.sock:
            # Форматуємо команду у вигляді протоколу: TEXT@Автор@Повідомлення
            data = f"TEXT@{self.username}@{message}\n"
            try:
                self.sock.sendall(data.encode('utf-8'))  # Кодуємо текст у байти для мережі
                self.add_message(message, author=self.username)
            except Exception as e:
                print(f"Помилка відправки: {e}")
                self.add_message("Помилка відправки", author="SYSTEM")
        self.message_entry.delete(0, END)  # Очищаємо поле вводу після відправки

    def recv_message(self):
        """Фоновий потік: неперервно чекає та приймає нові дані від сервера."""
        if not self.sock:
            return
        buffer = ""
        while True:
            try:
                chunk = self.sock.recv(4096)  # Зчитуємо порцію даних до 4 КБ
                if not chunk:
                    break
                buffer += chunk.decode('utf-8', errors='ignore')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.handle_line(line.strip())
            except OSError:
                break
        if self.sock:
            self.sock.close()

    def handle_line(self, line):
        """Розбирає отриманий від сервера рядок (текст чи зображення)."""
        if not line:
            return
        parts = line.split("@", 3)
        msg_type = parts[0]
        if msg_type == "TEXT":
            author, message = parts[1], parts[2]
            if author != self.username:
                self.add_message(message, author=author)
        elif msg_type == "IMAGE":
            author, filename, b64_img = parts[1], parts[2], parts[3]
            try:
                # Декодуємо картинку з Base64 тексту назад у бінарне зображення
                img_data = base64.b64decode(b64_img)
                pil_img = Image.open(io.BytesIO(img_data))
                ctk_img = CTkImage(pil_img, size=(200, 200))
                if author != self.username:
                    self.add_message(f"Надіслав(ла) зображення: {filename}", img=ctk_img, author=author)
            except Exception as e:
                self.add_message(f"Помилка зображення: {e}", author="SYSTEM")
        else:
            self.add_message(line, author="SYSTEM")

    def open_image(self):
        """Відкриває діалогове вікно для вибору картинки з ПК та надсилає її в чат."""
        file_name = filedialog.askopenfilename()
        if not file_name or not self.sock:
            return
        try:
            with open(file_name, "rb") as f:
                raw = f.read()
            # Перетворюємо бінарні байти файлу картинки у текст Base64
            b64_data = base64.b64encode(raw).decode('utf-8')
            short_name = os.path.basename(file_name)
            data = f"IMAGE@{self.username}@{short_name}@{b64_data}\n"
            self.sock.sendall(data.encode('utf-8'))
            self.add_message('Я надіслав(ла) зображення:', CTkImage(Image.open(file_name), size=(200, 200)),
                             author=self.username)
        except Exception as e:
            self.add_message(f"Помилка надсилання: {e}", author="SYSTEM")


# ==============================================================================
# 🏁 ТОЧКА ВХОДУ (Запуск нашої програми)
# ==============================================================================
if __name__ == "__main__":
    win = MainWindow()  # Створюємо екземпляр нашого вікна
    win.mainloop()      # Запускаємо безкінечний цикл обробки подій (кліків мишки, клавіатури)
