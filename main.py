#!/usr/bin/env python3
# encoding: utf-8


"""
@version: 1.4.8
@Python version:3.6
@author: frostnotfall
@license: MIT License
@contact: frostnotfall@gmail.com
@software: douban_movie_comments_keywords
"""

import datetime
import logging
from functools import wraps

from flask import Flask, request
from telegram import (Bot, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                      ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (Dispatcher, CallbackQueryHandler, CommandHandler, Filters, MessageHandler,
                          Updater)

import douban_movie_comments as dmc
import util
from config import token, host

## 使用 webhook 方式
app = Flask(__name__)
bot = Bot(token=token)
dispatcher = Dispatcher(bot, None)

## 使用轮询方式
# updater = Updater(TOKEN)
# dispatcher = updater.dispatcher

bot.setWebhook('https://{host}/{token}'.format(host=host, token=token))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


@app.route('/' + token, methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return 'ok'


# decorater:不用每定义一个函数都要用handler以及add_handler
def command(handler, cmd=None, **kw):
    def decorater(func):
        def wrapper(*args, **kw):
            return func(*args, **kw)

        if cmd is None:
            func_hander = handler(func, **kw)
        else:
            func_hander = handler(cmd, func, **kw)
        dispatcher.add_handler(func_hander)
        return wrapper

    return decorater


def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(*args, **kwargs):
        bot, update = args
        bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(bot, update, **kwargs)

    return command_func


# 命令：/start，入口，发送 customKeyboardButton
@command(CommandHandler, 'start')
@send_typing_action
def start(bot, update):
    start_time = datetime.datetime.now()

    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + '使用机器人')

    button_list = [
        KeyboardButton(text="正在热映"),
        KeyboardButton(text="电影搜索"),
        KeyboardButton(text="即将上映"),
        KeyboardButton(text="新片榜")
    ]
    reply_markup = ReplyKeyboardMarkup(util.build_menu(button_list, n_cols=2),
                                       resize_keyboard=True,
                                       one_time_keyboard=True)
    bot.send_message(chat_id=update.message.chat_id,
                     text="请根据下方按钮选择功能",
                     reply_markup=reply_markup)

    end_time = datetime.datetime.now()
    print("入口-执行时间:", end_time - start_time)


# “正在热映”功能，自定义的消息过滤方法，
@command(MessageHandler, util.FilterNowplaying('正在热映'))
@send_typing_action
def now_playing(bot, update):
    start_time = datetime.datetime.now()

    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 获取电影列表')

    movie_list = dmc.load()

    button_list = []
    for i in movie_list:
        button_list.append(InlineKeyboardButton(i['name'], callback_data=i['id']))
    reply_markup = InlineKeyboardMarkup(util.build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text="以下是正在热映的电影，请点击按钮查看详情",
                     reply_markup=reply_markup)

    end_time = datetime.datetime.now()
    print("正在热映-执行时间:", end_time - start_time)


# “新片榜”功能，自定义的消息过滤方法，发送 InlineKeyboardButton
@command(MessageHandler, util.FilterNowplaying('新片榜'))
@send_typing_action
def coming(bot, update):
    start_time = datetime.datetime.now()

    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 使用新片榜')

    movie_list, id_list = dmc.new_movies()
    range_len_movie_list = range(len(movie_list))
    button_list = []
    for i in range_len_movie_list:
        button_list.append(InlineKeyboardButton(movie_list[i], callback_data=id_list[i]))
    reply_markup = InlineKeyboardMarkup(util.build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text="以下是电影新片榜，请点击按钮查看详情",
                     reply_markup=reply_markup)

    end_time = datetime.datetime.now()
    print("新片榜-执行时间:", end_time - start_time)


# “即将上映”功能，自定义的消息过滤方法，发送 InlineKeyboardButton
@command(MessageHandler, util.FilterNowplaying('即将上映'))
@send_typing_action
def coming(bot, update):
    start_time = datetime.datetime.now()

    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 使用即将上映')

    movie_list, id_list = dmc.coming()
    range_len_movie_list = range(len(movie_list))
    button_list = []
    for i in range_len_movie_list:
        button_list.append(InlineKeyboardButton(movie_list[i], callback_data=id_list[i]))
    reply_markup = InlineKeyboardMarkup(util.build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text="以下是即将上映的电影，请点击按钮查看详情",
                     reply_markup=reply_markup)

    end_time = datetime.datetime.now()
    print("即将上映-执行时间:", end_time - start_time)


# “即将上映”功能，使用默认的消息过滤方法，必须放最下面，否则位于本方法下方的代码数据返回不正确
@command(MessageHandler, Filters.text)
@send_typing_action
def movie_search(bot, update):
    start_time = datetime.datetime.now()

    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 使用电影搜索')

    movie_name = update.message.text
    if movie_name == '电影搜索':
        bot.send_message(chat_id=update.message.chat_id,
                         text="请输入电影名称")

    if movie_name != '电影搜索':
        movie_list, id_list = dmc.movie_search(movie_name)

        range_len_movie_list = range(len(movie_list))
        button_list = []
        for i in range_len_movie_list:
            button_list.append(InlineKeyboardButton(movie_list[i], callback_data=id_list[i]))

        reply_markup = InlineKeyboardMarkup(util.build_menu(button_list, n_cols=2))
        bot.send_message(chat_id=update.message.chat_id,
                         text="请选择以下电影查看详情",
                         reply_markup=reply_markup)

    end_time = datetime.datetime.now()
    print("电影搜索-执行时间:", end_time - start_time)


# InlineKeyButton回调处理，生成电影详情
@command(CallbackQueryHandler, pattern='[0-9]+')
@send_typing_action
def movie_keyboard(bot, update):
    start_time = datetime.datetime.now()

    id_ = update.callback_query.data
    user_name = update.callback_query.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 查询电影，ID：' + id_)

    movie_image_text, title_text, directors_text, score, countries, genres, actors_text, summary = dmc.movie_info(
        id_)

    bot.send_message(chat_id=update.callback_query.message.chat_id,
                     text="{movie_image}"
                          "*电影名称*：{title}\n\n"
                          "*导演*：{directors}\n"
                          "*评分*：{score}\n"
                          "*制片国家/地区*：{countries}\n"
                          "*类型*：{genres}\n"
                          "*主演*：{actors}\n"
                          "*剧情简介*：{summary}\n".format(movie_image=movie_image_text,
                                                      title=title_text,
                                                      directors=directors_text,
                                                      score=score,
                                                      countries=countries,
                                                      genres=genres,
                                                      actors=actors_text,
                                                      summary=summary),
                     parse_mode=ParseMode.MARKDOWN)

    if score != 0:
        try:
            bot.send_photo(chat_id=update.callback_query.message.chat_id,
                           photo=open("./img/" + id_ + '.jpg', 'rb'))
            print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + "读取预缓存图片")
        except FileNotFoundError:
            print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
                  '：电影ID：' + id_ + " 未缓存，正在请求URL获取评论")
            msg_id = bot.send_message(chat_id=update.callback_query.message.chat_id,
                                      text="正在遍历该电影所有影评\n由于评论有几万条，请耐心等待").message_id

            dmc.save_img(id_)
            bot.send_photo(chat_id=update.callback_query.message.chat_id,
                           photo=open("./img/" + id_ + '.jpg', 'rb'))
            bot.delete_message(chat_id=update.callback_query.message.chat_id, message_id=msg_id)
        finally:
            bot.answer_callback_query(callback_query_id=update.callback_query.id)

    end_time = datetime.datetime.now()
    print("电影详情-执行时间:", end_time - start_time)


# 命令：/test，测试用途
@command(CommandHandler, 'test')
@send_typing_action
def start(bot, update):
    # bot.send_photo(chat_id=update.message.chat_id, photo='https://telegram.org/img/t_logo.png')
    bot.send_message(chat_id=update.message.chat_id,
                     text="<a href='https://i.stack.imgur.com/iqJTR.jpg' rel='nofollow noreferrer'>caption sample\n666\n</a>"
                          "<a href='https://telegram.org/img/t_logo.png' rel='nofollow noreferrer'>111\n222</a>",
                     parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    util.save_cookie()

    ## 轮询方式
    # updater.start_polling()

    ## webhook 方式
    app.run(host='127.0.0.1',
            port=8443,
            debug=True)

    ## 预缓存，默认不开启
    # util.background()
