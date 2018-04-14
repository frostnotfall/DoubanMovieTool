#!/usr/bin/env python3
# encoding: utf-8


"""
@version: 1.2.3
@Python version:3.6
@author: frostnotfall
@license: MIT License
@contact: frostnotfall@gmail.com
@software: douban_movie_comments_keywords
"""


import datetime
import logging

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler, CommandHandler, Updater)

import douban_movie_comments as dmc
import util
from config import TOKEN

updater = Updater(TOKEN)
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


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


@command(CommandHandler, 'start')
def start(bot, update):
    start_time = datetime.datetime.now()
    user_name = update.message.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 获取电影列表')
    movie_list = dmc.load()
    movie_str_list = []
    button_list = []
    for i in movie_list:
        movie_str_list.append(i['name'])
        button_list.append(InlineKeyboardButton(i['name'], callback_data=i['id']))
    reply_markup = InlineKeyboardMarkup(util.build_menu(button_list, n_cols=2))
    bot.send_message(chat_id=update.message.chat_id,
                     text="请选择以下电影",
                     reply_markup=reply_markup)
    end_time = datetime.datetime.now()
    print("执行时间:", end_time - start_time)


@command(CallbackQueryHandler)
def options(bot, update):
    start_time = datetime.datetime.now()
    id_ = update.callback_query.data
    user_name = update.callback_query.from_user.username
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + '用户 ' +
          user_name + ' 查询电影，ID：' + id_)
    try:
        bot.send_photo(chat_id=update.callback_query.message.chat_id,
                       photo=open("./img/" + id_ + '.jpg', 'rb'))
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + "读取预缓存图片")
    except FileNotFoundError:
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
              '：电影ID：' + id_ + " 未缓存，正在请求URL获取评论")
        bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                        text="正在遍历该电影所有影评\n由于评论有几万条，请耐心等待")
        dmc.save_img(id_)
        bot.send_photo(chat_id=update.callback_query.message.chat_id,
                       photo=open("./img/" + id_ + '.jpg', 'rb'))
    finally:
        bot.answer_callback_query(callback_query_id=update.callback_query.id)
        end_time = datetime.datetime.now()
        print("执行时间:", end_time - start_time)


if __name__ == '__main__':

    updater.start_polling()
    
    util.save_cookie()

    # 预缓存，默认不开启
    # util.background()
