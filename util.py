#!/usr/bin/env python3
# encoding: utf-8


import datetime
import os
import random
import threading
import time
from http import cookiejar
from urllib import request
import requests
import re

from telegram.ext import (BaseFilter)

import funcs

ua = [
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko)\
     Chrome/62.0.3202.94 YaBrowser/17.11.0.2191 Yowser/2.5 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
     Chrome/64.0.3282.189 Safari/537.36 Vivaldi/1.95.1077.60",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
     Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko)\
     Chrome/50.0.2661.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)\
     Chrome/64.0.3282.189 Safari/537.36 Vivaldi/1.95.1077.60"
]
ua = random.choice(ua)
head = {'Connection': 'Keep-Alive',
        'Accept': 'text/html,application/xhtml+xml,application/xml;'
                  'q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'User-Agent': ua
        }


def save_cookie():
    filename = 'cookie.txt'
    cookie = cookiejar.MozillaCookieJar(filename)
    opener = request.build_opener(request.HTTPCookieProcessor(cookie))
    header = []

    for key, value in head.items():
        elem = (key, value)
        header.append(elem)
    opener.add_headers = header

    opener.open('https://movie.douban.com')
    cookie.save(ignore_discard=True, ignore_expires=True)


def my_opener():
    cookie = cookiejar.MozillaCookieJar()
    cookie.load('cookie.txt', ignore_discard=True, ignore_expires=True)

    opener = request.build_opener(request.HTTPCookieProcessor(cookie))
    header = []

    for key, value in head.items():
        elem = (key, value)
        header.append(elem)
    opener.add_headers = header
    return opener


class MyThread(threading.Thread):

    def __init__(self, func, args=()):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args
        self.result = None

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except AttributeError:
            return None


class CustomFilter(BaseFilter):
    def __init__(self, text):
        self.text = text

    def filter(self, message):
        # return self.text in message.text
        if re.search(self.text, message.text):
            return True


# 定义菜单按钮
def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]

    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


# 预缓存 - 正在热映
def preload():
    def preload_img():
        movie_list, *_ = funcs.load()
        for i in movie_list:
            if os.path.exists(os.getcwd() + "./img/" + i['id'] + '.jpg') is False:
                print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
                      '：' + "预缓存，电影ID：" + i['id'])
                funcs.save_img(i['id'])
                time.sleep(60)

    time.sleep(600)
    t = threading.Thread(target=preload_img)
    print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + "周期性任务 - 预缓存")
    t.setDaemon(True)
    t.start()


def removal():
    def remove_img():
        time.sleep(21600)
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' + "周期性任务 - 清除词云图片")
        for item in os.listdir(os.getcwd() + "/img"):
            os.remove(os.path.join(os.getcwd() + "/img", item))

    s = threading.Thread(target=remove_img)
    s.setDaemon(True)
    s.start()

