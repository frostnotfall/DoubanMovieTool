#!/usr/bin/env python3
# encoding: utf-8


import asyncio
import datetime
import random
import threading
import time
from http import cookiejar
from pathlib import Path

import aiohttp
import requests
import ujson
from telegram.ext import (BaseFilter)

import data_funcs

ua = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/78.0.3904.99 Safari/537.36 Vivaldi/2.9.1705.41",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0",
    "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) "
    "Version/11.0 Mobile/15A5341f Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363"
]

head = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,""image/webp,"
              "image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "DNT": "1",
    "Host": "movie.douban.com",
    "Pragma": "no-cache",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": random.choice(ua)
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


def my_opener():
    filename = 'cookie.txt'
    session = requests.Session()
    session.cookies = cookiejar.MozillaCookieJar(filename)
    session.headers.update(head)
    session.get('https://movie.douban.com')
    session.cookies.save(ignore_discard=True, ignore_expires=True)

    return session


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
