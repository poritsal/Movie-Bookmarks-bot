import telebot
from telebot import types
import requests
import sqlite3
import json

TOKEN = '6313155683:AAFIhi1Hc4Z_SWreO9LcqVtzzoDD3yfbXrw'
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        movie_id INTEGER,
        name TEXT,
        year INTEGER
    )
    ''')
    conn.commit()
    cursor.close()
    conn.close()


def get_movie_info(movie_name):
    url = f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={movie_name}"
    headers = {"X-API-KEY": "00573bb8-7c43-4495-9c83-1ef6e732e25e"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        movie_data = response.json()
        return movie_data.get('films', [])
    else:
        print(f"Ошибка {response.status_code}: {response.text}")
        return None


def get_movie_details(film_id):
    url = f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{film_id}"
    headers = {"X-API-KEY": "00573bb8-7c43-4495-9c83-1ef6e732e25e"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        movie_data = response.json()

        poster_url = movie_data.get("posterUrlPreview", "")
        description = movie_data.get("description", "")
        nameRu = movie_data.get("nameRu", "")
        year = movie_data.get("year", "")

        return poster_url, description, nameRu, year
    else:
        print(f"Ошибка {response.status_code}: {response.text}")
        return None, None, None, None


def get_favorites(user_id):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT movie_id, name, year FROM favorites WHERE user_id = ?
    ''', (user_id,))

    favorites = cursor.fetchall()

    cursor.close()
    conn.close()

    return favorites

def add_to_favorites(user_id, film_id):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    poster_url, description, nameRu, year = get_movie_details(film_id)
    cursor.execute("INSERT INTO favorites (user_id, movie_id, name, year) VALUES (?, ?, ?, ?)",
                   (user_id, film_id, nameRu, year))

    conn.commit()
    cursor.close()
    conn.close()

def remove_favorite(user_id, movie_id):
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id))
    conn.commit()

    cursor.close()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    bot.send_message(message.chat.id, "Привет! Я бот для любителей кино.")

@bot.message_handler(commands=['add'])
def search_movie(message):
    bot.send_message(message.chat.id, "Введите название фильма:")
    bot.register_next_step_handler(message, process_movie_search)

def process_movie_search(message):
    chat_id = message.chat.id
    movie_name = message.text
    movies = get_movie_info(movie_name)

    if movies:
        keyboard = telebot.types.InlineKeyboardMarkup()

        num_movies_to_display = min(4, len(movies))

        for movie in movies[:num_movies_to_display]:
            callback_button = telebot.types.InlineKeyboardButton(
                text=f"{movie['nameRu']} ({movie['year']})",
                callback_data=f"info_{movie['filmId']}"
            )
            keyboard.add(callback_button)

        callback_button_more = telebot.types.InlineKeyboardButton(
            text="Уточнить запрос",
            callback_data="repeat"
        )
        keyboard.add(callback_button_more)

        bot.send_message(chat_id, "Выберите фильм: ", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "Фильмы не найдены.")


@bot.message_handler(commands=['remove'])
def remove_movie(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    favorites = get_favorites(user_id)

    if favorites:
        page = 1
        items_per_page = 5
        total_pages = -(-len(favorites) // items_per_page)

        show_page(chat_id, favorites, page, items_per_page, total_pages)
    else:
        bot.send_message(chat_id, "У вас пока нет любимых фильмов.")

def show_page(chat_id, favorites, page, items_per_page, total_pages):
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page

    keyboard = telebot.types.InlineKeyboardMarkup()

    for fav in favorites[start_idx:end_idx]:
        movie_id, name, year = fav
        callback_button = telebot.types.InlineKeyboardButton(
            text=f"{name} ({year})",
            callback_data=f"remove_{movie_id}"
        )
        keyboard.add(callback_button)

    if total_pages > 1:
        page_buttons = []
        if page > 1:
            page_buttons.append(telebot.types.InlineKeyboardButton(
                text="<< Назад",
                callback_data=f"removepage_{page-1}"
            ))
        if page < total_pages:
            page_buttons.append(telebot.types.InlineKeyboardButton(
                text="Вперед >>",
                callback_data=f"removepage_{page+1}"
            ))
        keyboard.add(*page_buttons)

    bot.send_message(chat_id, f"Страница {page}/{total_pages}:", reply_markup=keyboard)

@bot.message_handler(commands=['favorites'])
def show_favorites(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    favorites = get_favorites(user_id)

    if favorites:
        page = 1
        items_per_page = 5
        total_pages = -(-len(favorites) // items_per_page)

        send_page(chat_id, favorites, page, items_per_page, total_pages)
    else:
        bot.send_message(chat_id, "У вас пока нет любимых фильмов.")

def send_page(chat_id, favorites, page, items_per_page, total_pages):
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page

    keyboard = telebot.types.InlineKeyboardMarkup()

    for fav in favorites[start_idx:end_idx]:
        movie_id, name, year = fav
        callback_button = telebot.types.InlineKeyboardButton(
            text=f"{name} ({year})",
            callback_data=f"info_{movie_id}"
        )
        keyboard.add(callback_button)

    if total_pages > 1:
        page_buttons = []
        if page > 1:
            page_buttons.append(telebot.types.InlineKeyboardButton(
                text="<< Назад",
                callback_data=f"showpage_{page-1}"
            ))
        if page < total_pages:
            page_buttons.append(telebot.types.InlineKeyboardButton(
                text="Вперед >>",
                callback_data=f"showpage_{page+1}"
            ))
        keyboard.add(*page_buttons)

    bot.send_message(chat_id, f"Страница {page}/{total_pages}:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data.startswith("info_"):
        film_id = int(call.data.split("_")[1])
        poster_url, description, nameRu, year = get_movie_details(film_id)

        keyboard = types.InlineKeyboardMarkup()
        callback_button_add = types.InlineKeyboardButton(
            text="Добавить в любимое",
            callback_data=f"adding_{film_id}"
        )
        keyboard.add(callback_button_add)

        bot.send_photo(chat_id, poster_url, caption=description, reply_to_message_id=message_id, reply_markup=keyboard)

    elif call.data == "repeat":
        bot.send_message(chat_id, "К сожалению, по вашему запросу ничего не найдено...", reply_to_message_id=message_id)

    elif call.data.startswith("adding_"):
        film_id = int(call.data.split("_")[1])
        add_to_favorites(chat_id, film_id)
        bot.send_message(chat_id, f"Фильм добавлен в ваш список любимых", reply_to_message_id=message_id)

    elif call.data.startswith("showpage_"):
        page = int(call.data.split("_")[1])
        items_per_page = 5
        total_favorites = len(get_favorites(call.from_user.id))
        total_pages = -(-total_favorites // items_per_page)

        if 1 <= page <= total_pages:
            send_page(chat_id, get_favorites(call.from_user.id), page, items_per_page, total_pages)
        else:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text="Ошибка: Недопустимая страница.")

    elif call.data.startswith("removepage_"):
        page = int(call.data.split("_")[1])
        items_per_page = 5
        total_favorites = len(get_favorites(call.from_user.id))
        total_pages = -(-total_favorites // items_per_page)

        if 1 <= page <= total_pages:
            show_page(chat_id, get_favorites(call.from_user.id), page, items_per_page, total_pages)
        else:
            bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text="Ошибка: Недопустимая страница.")

    elif call.data.startswith("remove_"):
        film_id = int(call.data.split("_")[1])
        remove_favorite(call.from_user.id, film_id)
        bot.answer_callback_query(callback_query_id=call.id, show_alert=True, text="Фильм удален из списка любимых.")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Неизвестная команда")

bot.infinity_polling()