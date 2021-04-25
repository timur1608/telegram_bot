import time
from telebot import TeleBot, types
from telethon import TelegramClient
from bs4 import BeautifulSoup
import lxml
from sqliter import Sqliter
import config
from urllib import parse
import requests
import os
from random import shuffle

bot = TeleBot(config.token)


def main():
    bot.polling()


@bot.message_handler(commands=['help'])
def help(message):
    '''
    Справка о боте
    :param message:
    :return:
    '''
    bot.send_message(message.chat.id, 'Нажав на кнопку IT новости, вы можете посмотреть актуальные новости о мире IT')
    bot.send_message(message.chat.id,
                     'Нажав на кнопку Books, вы можете найти книгу по программированию на языке python и скачать ее за 1 монету')


@bot.message_handler(commands=["start"])
def inline(message):
    '''
    Начальный набор кнопок на клавиатуре
    :param message:
    :return:
    '''
    show_buttons(message.chat.id)

    data = Sqliter('db/quiz.sqlite', 'balance')
    data.create_user(message.chat.id)  # creating new user and putting him to db
    data.close()


@bot.callback_query_handler(func=lambda c: True)
def inline(x):
    '''
    Функция, которая срабатывает при нажатии на кнопку
    :param x:
    :return:
    '''
    if x.data == 'get_news':
        url = 'https://habr.com/ru/news/'
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        quotes = soup.find_all('a', class_='post__title_link')
        for i in quotes:
            bot.send_message(x.message.chat.id, f"[{i.text}]({i['href']})", parse_mode='Markdown',
                             disable_web_page_preview=True)
        show_buttons(x.message.chat.id)
    if x.data == 'quiz':
        data = Sqliter('db/quiz.sqlite', 'quiz')
        question = data.select_question(x.message.chat.id)
        data.close()
        with open(f'short_file_for_{x.message.chat.id}.txt', 'w') as file:
            file.write(str(question[0]))
        key = generate_markup(question[2], question[3])
        send = bot.send_message(x.message.chat.id, question[1], reply_markup=key)
        bot.register_next_step_handler(send, select_question)
    if x.data == 'book':
        data = Sqliter('db/quiz.sqlite', 'balance')
        balance = data.select_user(x.message.chat.id)
        if balance < 5:
            bot.send_message(x.message.chat.id,
                             'К сожалению, ваш баланс меньше 5, пройдите тест, чтобы заработать больше монет')
            show_buttons(x.message.chat.id)
        else:
            send = bot.send_message(x.message.chat.id, 'Введите название или часть названия книги, автора ниже:')
            bot.register_next_step_handler(send, searching_book)
        data.close()
    if x.data == 'balance':
        data = Sqliter('db/quiz.sqlite', 'balance')
        balance = data.select_user(x.message.chat.id)
        bot.send_message(x.message.chat.id, f'Ваш баланс: {balance}')
        show_buttons(x.message.chat.id)


def searching_book(message):
    '''
    Поиск книги по названию или по автору
    :param message:
    :return:
    '''
    bot.send_message(message.chat.id, 'Выполняется поиск, пожалуйста, подождите... (около 3 минут)')
    list_of_books = list()
    correct_list_of_books = list()
    for i in range(5):
        url = f'https://codernet.ru/books/python/?page={i + 1}'
        response_2 = requests.get(url)
        soup_2 = BeautifulSoup(response_2.text, 'lxml')
        quotes_2 = soup_2.find_all('li', class_='media')
        for i in quotes_2:
            list_of_books.append((i.a['title'], 'https://codernet.ru/' + i.a['href'][:-1]))
    f = False
    for j, i in enumerate(list_of_books):
        string = "%20".join(i[0].split()) + i[1][i[1].rfind('/'):] + ".pdf"
        href = parse.urljoin('https://codernet.ru/media/', string)
        try:
            res = requests.get(href.strip())
            if res.status_code != 404:
                correct_list_of_books.append((i[0], href))
        except Exception:
            print(f'{i[0]} ----эта книга не открывается')
    try:
        for j, i in enumerate(correct_list_of_books):
            if message.text.lower() in i[0].lower():
                f = True
                bot.send_message(message.chat.id, f'{j + 1}. {i[0]}')
        if not f:
            raise IOError
        send = bot.send_message(message.chat.id, 'Выберите номер книги')
        with open(f'short_file_for_{message.chat.id}.txt', 'w') as file:
            for i in correct_list_of_books:
                file.write('/////'.join(i) + '\n')
        bot.register_next_step_handler(send, choose_book)
    except IOError:
        bot.send_message(message.chat.id, 'К сожалению, не найдено книги по вашему запросу')
        show_buttons(message.chat.id)


def choose_book(message):
    '''
    Выбор книги из списка
    :param message:
    :return:
    '''
    with open(f'short_file_for_{message.chat.id}.txt', 'r') as file:
        current_list = file.read().splitlines()
    os.remove(f'short_file_for_{message.chat.id}.txt')
    specified_number = int(message.text)
    href = current_list[specified_number].split('/////')[1]
    try:
        response = requests.get(href, stream=True)
        with open(f'output_for_{message.chat.id}.pdf', 'wb') as file:
            file.write(response.content)
            bot.send_document(message.chat.id, open(f'output_for_{message.chat.id}.pdf', 'rb'))
            data = Sqliter('db/quiz.sqlite', 'balance')
            data.bought_book(message.chat.id)
            data.close()
    except Exception:
        bot.send_message(message.chat.id, 'Неверный формат ввода или размер книги слишком велик (больше 50 мб)')
    finally:
        if os.path.exists(f'output_for_{message.chat.id}.pdf'):
            os.remove(f'output_for_{message.chat.id}.pdf')
    show_buttons(message.chat.id)


def generate_markup(right_answer, wrong_answers):
    """
    Создаем кастомную клавиатуру для выбора ответа
    :param right_answer: Правильный ответ
    :param wrong_answers: Набор неправильных ответов
    :return: Объект кастомной клавиатуры
    """
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    # Склеиваем правильный ответ с неправильными
    all_answers = '{};{}'.format(right_answer, wrong_answers)
    # Создаем лист (массив) и записываем в него все элементы
    list_items = []
    for item in all_answers.split(';'):
        list_items.append(item)
    # Хорошенько перемешаем все элементы, чтобы правильный ответ не был первым
    shuffle(list_items)
    # Заполняем разметку перемешанными элементами
    for item in list_items:
        markup.add(item)
    return markup


def show_buttons(user_id):
    '''
    Выводит кнопки на кастомной клавиатуре
    :param user_id:
    :return:
    '''
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(text="IT новости 📃", callback_data="get_news")
    but_2 = types.InlineKeyboardButton(text="Books 📖", callback_data="book")
    but_3 = types.InlineKeyboardButton(text="Random Quiz ❓", callback_data="quiz")
    but_4 = types.InlineKeyboardButton(text='Balance 💳', callback_data='balance')
    key.add(but_1, but_2, but_3, but_4)
    bot.send_message(user_id, 'Выберите то, что хотите узнать', reply_markup=key)


def select_question(message):
    with open(f'short_file_for_{message.chat.id}.txt') as file:
        res = file.read().splitlines()
    os.remove(f'short_file_for_{message.chat.id}.txt')
    data = Sqliter('db/quiz.sqlite', 'quiz')
    question = data.select_current_question(int(res[0]))
    if message.text == question[2]:
        data.update_balance(message.chat.id)
        bot.send_message(message.chat.id, 'Поздравляем, ваш баланс увеличился')
    else:
        bot.send_message(message.chat.id, 'К сожалению вы не правильно ответили на вопрос :(')
    data.close()

    # if message.text ==


if __name__ == '__main__':
    main()
