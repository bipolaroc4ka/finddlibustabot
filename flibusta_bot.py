import requests
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

 

# Настроим логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовый URL сайта
BASE_URL = "https://flibusta.is"

# Поиск книги
async def search_book(title):
    search_url = f"{BASE_URL}/booksearch"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(search_url, params={"ask": title}, headers=headers)
        if response.status_code != 200:
            return None, "Ошибка при подключении к Flibusta."
    
        soup = BeautifulSoup(response.text, "html.parser")
        ul_elements = soup.find('ul', attrs={'class': False, 'id': False, 'style': False})
        books = []
    
        if ul_elements:
            li_elements = ul_elements.find_all('li')
            for count, li in enumerate(li_elements, start=1):
                book_title = li.find('a').get_text(strip=False)
                book_url = BASE_URL + li.find('a').get('href')
                author = ""
                # Проверяем, есть ли второй элемент в списке ссылок
                links = li.find_all('a')
                if len(links) > 1:
                    author = links[1].get_text(strip=True)  # Если есть, извлекаем автора
                else:
                    author = ""  # Или указываем значение по умолчанию

                
                #author = li.find_all('a')[1].get_text(strip=True)
                books.append((count, book_title, author, book_url))
               
            return books, None
        else:
            return None, "Книги не найдены."
    except Exception as e:
        return None, "Произошла ошибка. Попробуйте позже"

# Получение ссылки для скачивания
async def get_download_link(book_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(book_url, headers=headers)
    
    if response.status_code != 200:
        return None, "Ошибка при подключении к странице книги."
    
    soup = BeautifulSoup(response.text, "html.parser")
    download_links = {
        "fb2": soup.find("a", href=True, text="(fb2)"),
        "epub": soup.find("a", href=True, text="(epub)"),
        "mobi": soup.find("a", href=True, text="(mobi)"),
        "pdf": soup.find("a", href=True, text="(скачать pdf)"),
    }
    
    links = {fmt: BASE_URL + link['href'] for fmt, link in download_links.items() if link}
    if not links:
        return None, "Ссылки для скачивания не найдены."
    return links, None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)
    user_name = update.effective_user.first_name  # Имя пользователя
    user_username = update.effective_user.username  # Логин пользователя (может быть None, если его нет)
    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=f"Пользователь (ID: {user_id}) Имя: {user_name} Логин: @{user_username} использовал команду /start."
    )
    await update.message.reply_text(
        "Привет! Я помогу найти и скачать книги с Flibusta.\n"
        "Введите команду /search <название книги>, чтобы начать."
    )

# Команда /search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Введите название книги после команды /search.")
        return
    
    book_title = " ".join(context.args)
    await update.message.reply_text(f"Ищу книги с названием: {book_title}...")
    
    books, error = await search_book(book_title)
    if error:
        await update.message.reply_text(error)
        return
    
    # Отправляем пользователю список книг
    keyboard = [
        [InlineKeyboardButton(f"{count}. {title} - {author}", callback_data=url)]
        for count, title, author, url in books
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите книгу из списка:", reply_markup=reply_markup)

# Обработка выбора книги
async def book_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    book_url = query.data
    await query.edit_message_text("Получаю ссылки для скачивания...")
    
    links, error = await get_download_link(book_url)
    if error:
        await query.edit_message_text(error)
        return
    
    reply_text = "Ссылки для скачивания:\n"
    for fmt, link in links.items():
        reply_text += f"{fmt}: {link}\n"
    await query.edit_message_text(reply_text)


 
# Основная функция
def main():
    application = Application.builder().token("Your Token").build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CallbackQueryHandler(book_selection))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
