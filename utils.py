#!/usr/bin/env python3
# encoding: utf-8


import asyncio
import datetime
import random
import threading
import time
import ujson
from http import cookiejar
from pathlib import Path
from urllib import request

import aiohttp
from telegram.ext import (BaseFilter)

import data_funcs

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


async def aiohttp_check_cookie():
    try:
        with open('cookies.json', 'r', encoding="UTF-8") as f:
            cookies = ujson.load(f)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(),
                                         headers=head,
                                         cookies=cookies) as session:
            async with session.get('https://movie.douban.com'):
                pass
    except (ValueError, FileNotFoundError):
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(),
                                         headers=head) as session:
            async with session.get('https://movie.douban.com') as res:
                cookies = session.cookie_jar.filter_cookies('https://movie.douban.com')
                for key, cookie in res.cookies.items():
                    cookies[cookie.key] = cookie.value
                with open('cookies.json', 'w') as f:
                    ujson.dump(cookies, f)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(aiohttp_check_cookie())

with open('cookies.json', 'r', encoding="UTF-8") as f:
    cookies = ujson.load(f)


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
    return opener


def my_opener():
    try:
        cookie = cookiejar.MozillaCookieJar()
        cookie.load('cookie.txt', ignore_discard=True, ignore_expires=True)
        opener = request.build_opener(request.HTTPCookieProcessor(cookie))
    except (FileNotFoundError, cookiejar.LoadError):
        opener = save_cookie()
    else:
        header = []

        for key, value in head.items():
            elem = (key, value)
            header.append(elem)
        opener.add_headers = header

    return opener


class CustomFilter(BaseFilter):
    def __init__(self, text):
        self.text = text

    def filter(self, message):
        return self.text in message.text


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


# 预缓存 - 正在热映中的电影的影评词云图片
def preload():
    def preload_img():
        *_, movie_id_list = data_funcs.load()
        img_dir = Path('img')
        for id_ in movie_id_list:
            if Path(img_dir, id_).exists() is False:
                print(f"{datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')}：预缓存，电影ID{id_}")
                data_funcs.save_img(id_)
                time.sleep(60)

    time.sleep(600)
    t = threading.Thread(target=preload_img)
    print(f"{datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')}：周期性任务 - 预缓存")
    t.setDaemon(True)
    t.start()


def removal():
    def remove_img():
        time.sleep(21600)
        print(f"{datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')}：周期性任务 - 清除词云图片")
        img_dir = Path('img')
        for img_file in img_dir.iterdir():
            Path.unlink(img_file)

    s = threading.Thread(target=remove_img)
    s.setDaemon(True)
    s.start()