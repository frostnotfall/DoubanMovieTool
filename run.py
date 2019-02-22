#!/usr/bin/env python3
# encoding: utf-8


"""
@Python version:3.6
@author: frostnotfall
@license: MIT License
@contact: frostnotfall@gmail.com
@software: DoubanMovieTool
"""

from flask import Flask, request
from telegram import Update

import bot_funcs
import utils

try:
    from config import token
except (ModuleNotFoundError, ImportError, NameError):
    print('请在config.py 中指定 token')
    exit()
try:
    from config import run_mode
except (ImportError, NameError):
    run_mode = 'polling'

global app

if run_mode == 'webhook':
    # 使用 webhook 方式
    app = Flask(__name__)


    @app.route(f'/{token}', methods=['POST'])
    def webhook_handler():
        if request.method == "POST":
            update = Update.de_json(request.get_json(force=True), bot_funcs.bot)
            bot_funcs.dispatcher.process_update(update)
        return 'ok'

if __name__ == '__main__':
    if run_mode == 'webhook':
        app.run(host='127.0.0.1', port=8443)
    elif run_mode == 'polling':
        bot_funcs.updater.start_polling()
    else:
        print('请在 config.py 指定运行方式, 可选： webhook 或者 polling')
        exit()

    # 定时清除词云图片
    utils.removal()

    # 预缓存正在热映中的电影的影评词云图片，默认不开启
    # utils.preload()
