#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import datetime
import json
import re
from urllib import parse

import aiohttp
import jieba
import lxml
import numpy
import pandas
from bs4 import BeautifulSoup
from wordcloud import WordCloud

import util


def load():
    with util.my_opener().open('https://movie.douban.com/cinema/nowplaying/beijing/') as html_res:
        html_data = html_res.read().decode('utf-8')

    soup = BeautifulSoup(html_data, 'lxml')
    nowplaying = soup.find('div', id='nowplaying')
    nowplaying_list = nowplaying.find_all('li', class_='list-item')

    movie_list = []
    for item in nowplaying_list:
        movie_dict = dict()
        movie_dict['id'] = item['data-subject']
        for tag_img_item in item.find_all('img'):
            movie_dict['name'] = item['data-title']
            movie_list.append(movie_dict)
    return movie_list


def coming():
    with util.my_opener().open('https://movie.douban.com/coming') as html_res:
        html_data = html_res.read().decode('utf-8')

    soup = BeautifulSoup(html_data, 'lxml')
    coming_list = soup.find('table', class_="coming_list").find('tbody')
    movie_list = list()
    id_list = list()
    for i in coming_list.find_all('a'):
        movie_name = i.text
        movie_url = i.get('href').strip("//")
        movie_id = re.search(r"\d+", movie_url).group()
        movie_list.append(movie_name)
        id_list.append(movie_id)

    return movie_list, id_list


def new_movies():
    with util.my_opener().open('https://movie.douban.com/chart') as html_res:
        html_data = html_res.read().decode('utf-8')

    soup = BeautifulSoup(html_data, 'lxml')
    movie_list = list()
    id_list = list()
    for i in soup.find_all('a', class_='nbg'):
        movie_name = i['title']
        movie_url = i.get('href').strip("//")
        movie_id = re.search(r"\d+", movie_url).group()
        movie_list.append(movie_name)
        id_list.append(movie_id)

    return movie_list, id_list


def movie_search(movie_name):
    with util.my_opener().open('https://api.douban.com/v2/movie/search?tag={}'.format(
            parse.quote(movie_name))) as html_data:
        json_data = json.loads(html_data.read().decode('utf-8'))

    subjects = json_data['subjects']
    movie_list = list()
    id_list = list()
    range_len_subjects = range(len(subjects))
    for i in range_len_subjects:
        movie_list.append(subjects[i]['title'])
        id_list.append(subjects[i]['id'])

    return movie_list, id_list


def movie_info(id_):
    with util.my_opener().open('https://api.douban.com/v2/movie/subject/' + str(id_)) as html_data:
        json_data = json.load(html_data)

        movie_image_text = '[.](' + json_data['images']['small'] + ')'

        title_text = '[' + json_data['title'] + '](https://movie.douban.com/subject/' + str(
            id_) + '/?from=playing_poster)'

        try:
            directors_text_list = list()
            for director_info in json_data['directors']:
                directors_text_list.append(
                    '[' + director_info['name'] + '](https://movie.douban.com/celebrity/' +
                    director_info[
                        'id'] + '/)')
            directors_text = '，'.join(directors_text_list)
        except TypeError:
            directors_text = '无'

        score = json_data['rating']['average']

        countries = json_data['countries']
        if isinstance(countries, list):
            countries = '，'.join(countries)

        genres = json_data['genres']
        if isinstance(genres, list):
            genres = '，'.join(genres)

        try:
            actors_text_list = list()
            for actor_info in json_data['casts']:
                actors_text_list.append(
                    '[' + actor_info['name'] + '](https://movie.douban.com/celebrity/' + actor_info[
                        'id'] + '/)')
            actors_text = '，'.join(actors_text_list)
        except TypeError:
            actors_text = '无'

        summary = json_data['summary']

    return movie_image_text, title_text, directors_text, score, countries, genres, actors_text, summary


def get_comments(id_):
    async def fetch(session, url):
        async with session.get(url) as response:
            return await response.text()

    async def parser(html):
        soup = BeautifulSoup(html, 'lxml')
        all_comment_div = soup.find('div', class_='mod-bd')

        comments_list = list()
        for item in all_comment_div.find_all('div', class_='comment'):
            each_comment_unformatted = item.find('p').find('span').string
            if each_comment_unformatted is not None:
                comments_list.append(each_comment_unformatted)

        comments_formatted = str()
        for k in range(len(comments_list)):
            comments_formatted = comments_formatted + (str(comments_list[k])).strip()

        # \u4e00-\u9fa5 Unicode汉字编码范围
        pattern = re.compile(r'[\u4e00-\u9fa5]+')
        comments_with_punctuation = re.findall(pattern, comments_formatted)
        pure_comments = ''.join(comments_with_punctuation)

        return pure_comments

    async def download(url):
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, url)
            pure_comments = await parser(html)
            return pure_comments

    urls = ['https://movie.douban.com/subject/' + str(id_) + '/comments?start=' + str(
        i * 20) + '&limit=20&sort=new_score&status=P'.format(i) for i in range(11)]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [asyncio.ensure_future(download(url)) for url in urls]
    loop.run_until_complete(asyncio.wait(tasks))

    all_final_comments = str()
    for task in tasks:
        all_final_comments = all_final_comments + task.result()

    return all_final_comments


def save_img(id_):
    text = get_comments(id_)

    jieba.setLogLevel('ERROR')
    segment = jieba.lcut(text)
    word_df = pandas.DataFrame({'segment': segment})

    stopwords = pandas.read_csv("stopwords.txt", index_col=False,
                                quoting=3, sep="\t", names=['stopword'], encoding='utf-8')
    words_df = word_df[~word_df.segment.isin(stopwords.stopword)]

    words_stat = words_df.groupby(by=['segment'])['segment'].agg([numpy.size]) \
        .rename(columns={"size": "计数"})
    words_stat = words_stat.reset_index().sort_values(by=["计数"], ascending=False)

    wordcloud = WordCloud(font_path="simhei.ttf",
                          background_color="white",
                          scale=3)
    word_frequency = {x[0]: x[1] for x in words_stat.head(1000).values}

    word_frequency_list = []
    for key in word_frequency:
        temp = (key, word_frequency[key])
        word_frequency_list.append(temp)

    # mpl.rcParams['figure.figsize'] = (5.0, 2.5)

    try:
        wordcloud = wordcloud.fit_words(dict(word_frequency_list))
    except ValueError:
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
              '：' + "电影ID：" + id_ + " 获取评论失败")
        return
    wordcloud.to_file("./img/" + id_ + ".jpg")

    # plt.imshow(wordcloud)
    # plt.xticks([])
    # plt.yticks([])
    # plt.gca().xaxis.set_major_locator(plt.NullLocator())
    # plt.gca().yaxis.set_major_locator(plt.NullLocator())
    # plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    # plt.margins(0, 0)
    # plt.savefig("./img/" + id_ + ".jpg", transparent=True, dpi=300, pad_inches=0, bbox_inches='tight')
