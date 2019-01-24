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

    movie_list = list()
    movie_id_list = list()
    for item in nowplaying_list:
        movie_id_list.append('movie ' + item['data-subject'])
        movie_list.append(item['data-title'])
    return movie_list, movie_id_list


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
    movie_id_list = list()
    for i in soup.find_all('a', class_='nbg'):
        movie_name = i['title']
        movie_url = i.get('href').strip("//")
        movie_id = re.search(r"\d+", movie_url).group()
        movie_list.append(movie_name)
        movie_id_list.append('movie ' + movie_id)

    return movie_list, movie_id_list


def movie_search(movie_name):
    with util.my_opener().open('https://api.douban.com/v2/movie/search?tag={}'.format(
            parse.quote(movie_name))) as html_data:
        json_data = json.loads(html_data.read().decode('utf-8'))

    subjects = json_data['subjects']
    movie_list = list()
    movie_id_list = list()
    range_len_subjects = range(len(subjects))
    for i in range_len_subjects:
        movie_list.append(subjects[i]['title'])
        movie_id_list.append('movie ' + subjects[i]['id'])

    return movie_list, movie_id_list


def actor_search(actor_name):
    with util.my_opener().open('https://movie.douban.com/celebrities/search?search_text={}'.format(
            parse.quote(actor_name))) as html_res:
        html_data = html_res.read().decode('UTF-8')

    soup = BeautifulSoup(html_data, 'lxml')
    actor_list = list()
    actor_id_list = list()
    search_result = soup.find_all('h3')
    for each_result in search_result:
        actor_name = each_result.string
        actor_url = each_result.find('a').get('href')
        actor_id = re.search(r"\d+", actor_url).group()
        actor_list.append(actor_name)
        actor_id_list.append('actor ' + actor_id)

    return actor_list, actor_id_list


def movie_info(id_):
    with util.my_opener().open('https://api.douban.com/v2/movie/subject/' + str(id_)) as html_data:
        json_data = json.load(html_data)

        movie_image_text = json_data['images']['small']

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


def actor_info(id_):
    with util.my_opener().open('https://movie.douban.com/celebrity/{id}/'.format(id=id_)) as html_res:
        html_data = html_res.read().decode('UTF-8')

        soup = BeautifulSoup(html_data, 'lxml')
        headline = soup.find('div', id='headline', class_="item")
        actor_name = headline.find('div', class_="pic").find('a', class_="nbg").get('title')
        actor_pic_url = headline.find('div', class_="pic").find('a', class_="nbg").get('href')

        actor_html = '<a href="https://movie.douban.com/celebrity/{id}/">{actor_name}</a>'.format(
            actor_name=actor_name, id=id_)

        actor_info_dict = {'sex': None, 'sign': None, 'birthday': None, 'birthplace': None,
                           'profession': None,
                           'more_foreign_name': None, 'more_chinese_name': None, 'families_html': None,
                           'imdb_nm_html': None, 'website_html': None}

        for ul_li in headline.find('ul').find_all('li'):
            span = ul_li.find('span')
            if str(span.string) == '性别':
                actor_info_dict['sex'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '星座':
                actor_info_dict['sign'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '出生日期':
                actor_info_dict['birthday'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '出生地':
                actor_info_dict['birthplace'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '职业':
                actor_info_dict['profession'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '更多外文名':
                actor_info_dict['more_foreign_name'] = span.next_sibling.strip(':').strip()
            if str(span.string) == '更多中文名':
                actor_info_dict['more_chinese_name'] = span.next_sibling.strip(':').strip()

        sex = actor_info_dict['sex'] if actor_info_dict['sex'] else '无'
        sign = actor_info_dict['sign'] if actor_info_dict['sign'] else '无'
        birthday = actor_info_dict['birthday'] if actor_info_dict['birthday'] else '无'
        birthplace = actor_info_dict['birthplace'] if actor_info_dict['birthplace'] else '无'
        profession = actor_info_dict['profession'] if actor_info_dict['profession'] else '无'
        more_foreign_name = actor_info_dict['more_foreign_name'] if actor_info_dict[
            'more_foreign_name'] else '无'
        more_chinese_name = actor_info_dict['more_chinese_name'] if actor_info_dict[
            'more_chinese_name'] else '无'
        families_html = actor_info_dict['families_html'] if actor_info_dict['families_html'] else '无'
        imdb_nm_html = actor_info_dict['imdb_nm_html'] if actor_info_dict['imdb_nm_html'] else '无'
        website_html = actor_info_dict['website_html'] if actor_info_dict['website_html'] else '无'

    return actor_pic_url, actor_html, sex, sign, birthday, birthplace, profession, more_foreign_name, more_chinese_name, families_html, imdb_nm_html, website_html


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

    try:
        wordcloud = wordcloud.fit_words(dict(word_frequency_list))
    except ValueError:
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
              '：' + "电影ID：" + id_ + " 获取评论失败")
        return
    wordcloud.to_file("./img/" + id_ + ".jpg")
