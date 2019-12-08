#!/usr/bin/env python3
# encoding: utf-8


import asyncio
import re
from urllib import parse

import aiohttp
import jieba
import numpy
import pandas
import ujson
from aiograph import Telegraph
from bs4 import BeautifulSoup
from wordcloud import WordCloud

import utils

# 数字编码范围
id_pattern = re.compile(r"\d+")
# \u4e00-\u9fa5 Unicode汉字编码范围
han_pattern = re.compile(r'[\u4e00-\u9fa5]+')
# imdb 链接
imdb_pattern = re.compile(r"^http://www.imdb.com")


def load():
    with utils.my_opener().get('https://movie.douban.com/cinema/nowplaying/beijing/') as html_res:
        html_data = html_res.text

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
    with utils.my_opener().get('https://movie.douban.com/coming') as html_res:
        html_data = html_res.text

    soup = BeautifulSoup(html_data, 'lxml')
    coming_list = soup.find('table', class_="coming_list").find('tbody')
    movie_list = list()
    movie_id_list = list()

    for i in coming_list.find_all('a'):
        movie_name = i.text
        movie_url = i.get('href').strip("//")
        movie_id = id_pattern.search(movie_url).group()
        movie_list.append(movie_name)
        movie_id_list.append('movie ' + movie_id)

    return movie_list, movie_id_list


def new_movies():
    with utils.my_opener().get('https://movie.douban.com/chart') as html_res:
        html_data = html_res.text

    soup = BeautifulSoup(html_data, 'lxml')
    movie_list = list()
    movie_id_list = list()

    for i in soup.find_all('a', class_='nbg'):
        movie_name = i['title']
        movie_url = i.get('href').strip("//")
        movie_id = id_pattern.search(movie_url).group()
        movie_list.append(movie_name)
        movie_id_list.append('movie ' + movie_id)

    return movie_list, movie_id_list


def top250(page_num):
    if page_num == 1:
        with utils.my_opener().get('https://movie.douban.com/top250') as html_res:
            html_data = html_res.text
    else:
        with utils.my_opener().get(f'https://movie.douban.com/top250?'
                                   f'start={str((page_num - 1) * 25)}&filter=') as html_res:
            html_data = html_res.text

    soup = BeautifulSoup(html_data, 'lxml')
    grid_view = soup.find('ol', class_='grid_view')

    movie_list = list()
    movie_id_list = list()

    for i in grid_view.find_all('div', class_='info'):
        movie_name = i.find('span', class_='title').text
        movie_list.append(movie_name)
        movie_url = i.div.a.get('href')
        movie_id = id_pattern.search(movie_url).group()
        movie_id_list.append('movie ' + movie_id)

    return movie_list, movie_id_list


def movie_search(movie_name):
    with utils.my_opener().get(
            f'https://api.douban.com/v2/movie/search?tag={parse.quote(movie_name)}') as html_data:
        json_data = ujson.loads(html_data.read().decode('utf-8'))

    subjects = json_data['subjects']
    movie_list = list()
    movie_id_list = list()
    range_len_subjects = range(len(subjects))

    for i in range_len_subjects:
        movie_list.append(subjects[i]['title'])
        movie_id_list.append(f'''movie {subjects[i]['id']}''')

    return movie_list, movie_id_list


def actor_search(actor_name):
    with utils.my_opener().get(
            f'https://movie.douban.com/celebrities/search?search_text={parse.quote(actor_name)}') \
            as html_res:
        html_data = html_res.text

    soup = BeautifulSoup(html_data, 'lxml')
    actor_list = list()
    actor_id_list = list()
    search_result = soup.find_all('h3')

    for each_result in search_result:
        actor_name = each_result.string
        actor_url = each_result.find('a').get('href')
        actor_id = id_pattern.search(actor_url).group()
        actor_list.append(actor_name)
        actor_id_list.append(f'actor {actor_id}')

    return actor_list, actor_id_list


def movie_info(id_):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegraph = Telegraph()

    async def get_info(id_):
        await telegraph.create_account('DoubanMovieBot')
        with utils.my_opener().get(f'https://movie.douban.com/subject/{id_}/') as html_res:
            html_data = html_res.text
        soup = BeautifulSoup(html_data, 'lxml')

        # json part
        json_data = ujson.loads(soup.find('script', type='application/ld+json').text)
        title = json_data['name']
        image_html = f'''<img src="{json_data['image']}">'''
        score = json_data['aggregateRating']['ratingValue']
        if score == '':
            score = '暂无评分'
        score_html = f'<strong>评分：</strong>{score}<br />'

        # rating part
        try:
            votes_num = soup.find('span', property="v:votes").text
            votes_num_html = f'<strong>评分人数：</strong>{votes_num}<br/>'
        except AttributeError:
            votes_num_html = f'<strong>评分人数：</strong>暂无评分人数<br/>'

        # info part
        info = soup.find('div', id='info')
        directors = str(info.find_all('a', rel="v:directedBy")).strip('[|]')
        directors_html = f'''<strong>导演：</strong>{directors if directors != '' else '暂无导演信息'}<br />'''
        try:
            author_html = f'''<strong>编剧：</strong>{str(
                info.find('span', text='编剧').next_sibling.next_sibling).replace('<span class="attrs">',
                                                                                '').replace('</span>',
                                                                                            '')}<br />'''
        except AttributeError:
            author_html = f'<strong>编剧：</strong>暂无编剧信息<br />'
        actors = str(info.find_all('a', rel="v:starring")).strip('[|]')
        actors_html = f'''<strong>主演：</strong>{actors if actors != '' else '暂无主演信息'}<br />'''
        genre_set = set()
        for genre in info.find_all('span', property="v:genre"):
            genre_set.add(genre.text)
        genre_html = f'''<strong>类型：</strong>{' / '.join(genre_set)}<br/>'''
        country_html = f'''<strong>制片国家/地区：</strong>{str(
            info.find('span', text='制片国家/地区:').next_sibling).strip()}<br />'''
        try:
            language_html = f'''<strong>语言：</strong>{
            str(info.find('span', text='语言:').next_sibling).strip()}<br />'''
        except AttributeError:
            language_html = f'''<strong>语言：</strong>暂无信息<br />'''
        publish_date_set = set()
        for publish_date in info.find_all('span', property="v:initialReleaseDate"):
            publish_date_set.add(publish_date.text)
        publish_date_html = f'''<strong>上映日期：</strong>{' / '.join(publish_date_set)}<br/>'''
        try:
            runtime = info.find('span', property="v:runtime").text
            runtime_html = f'<strong>片长：</strong>{runtime}<br/>'
        except AttributeError:
            runtime_html = f'<strong>片长：</strong>暂无信息<br/>'
        try:
            aka_html = f'''<strong>又名：</strong>{
            str(info.find('span', text='又名:').next_sibling).strip()}<br />'''
        except AttributeError:
            aka_html = f'''<strong>又名：</strong>暂无信息<br />'''
        imdb = str(info.find(href=imdb_pattern))
        imdb_html = f'''<strong>IMDb链接：</strong>{imdb if imdb is not None else '暂无imdb信息'}<br />'''
        info_html = f'{image_html}<h3>电影信息</h3>{score_html}{votes_num_html}{directors_html}' \
                    f'{author_html}{actors_html}{genre_html}{country_html}{language_html}{publish_date_html}' \
                    f'{runtime_html}{aka_html}{imdb_html}'
        info_html = info_html.replace('/celebrity', 'https://movie.douban.com/celebrity')

        # summary part
        related_info = soup.find('div', class_='related-info')
        try:
            summary = related_info.find('span', class_="all hidden").text.strip().replace(' ', '')
        except AttributeError:
            summary = related_info.find('span', property="v:summary").text.strip().replace(' ', '')
        summary_html = f'<h3>{related_info.h2.i.text}:</h3><p>{summary}</p>'

        # awards part
        if soup.find('div', class_='mod') is not None:
            with utils.my_opener().get(f'https://movie.douban.com/subject/{id_}/awards/') as html_res:
                html_data = html_res.text
            soup = BeautifulSoup(html_data, 'lxml')
            content = soup.find('div', id='content')
            awards_html = f'<h3>{content.h1.text}：</h3>'
            for awards in content.find_all('div', class_="awards"):
                awards_div_h2 = awards.div.h2
                awards_href = awards_div_h2.a.get('href')
                awards_name = awards_div_h2.get_text().replace('\n', '')
                awards_name_html = f'<br/><em><a href="{awards_href}">{awards_name}</a></em><br/>'
                awards_category_html = str(awards.find_all('ul')).strip('[|]').replace(
                    ', ', '').replace('<li></li>', '').replace('\n', '')
                awards_html = f'{awards_html}{awards_name_html}{awards_category_html}'
            page = await telegraph.create_page(title, f'{info_html}{summary_html}{awards_html}')
        else:
            page = await telegraph.create_page(title, f'{info_html}{summary_html}')
        print('生成电影Instant View， URL:', page.url)

        return page.url, score

    try:
        url, score = loop.run_until_complete(get_info(id_))
    finally:
        loop.run_until_complete(telegraph.close())

    return url, score


def actor_info(id_):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegraph = Telegraph()

    async def main():
        await telegraph.create_account('DoubanMovieBot')
        with utils.my_opener().get(f'https://movie.douban.com/celebrity/{id_}/') as html_res:
            html_data = html_res.text
        soup = BeautifulSoup(html_data, 'lxml')

        # info part
        headline = soup.find('div', id='headline', class_="item")
        actor_name = headline.find('div', class_="pic").find('a', class_="nbg").get('title')
        image_url = headline.find('div', class_="pic").find('a', class_="nbg").get('href')
        image_html = f'<img src="{image_url}">'
        ul = headline.find('ul', class_="")
        ul_html = str(ul).replace('span', 'strong').replace('\n', '').replace('  ', '')
        info_html = f'{image_html}<h3>影人信息</h3>{ul_html}'

        # summary part
        intro = soup.find('div', id="intro")
        try:
            summary = intro.find('span', class_="all hidden").text.strip().replace(' ', '')
        except AttributeError:
            summary = intro.find('div', class_="bd").text.strip().replace(' ', '')
        summary_html = f'<h3>影人简介:</h3><p>{summary}</p>'

        # awards part
        if soup.find('div', class_='mod').find('div', class_='hd') is not None:
            with utils.my_opener().get(f'https://movie.douban.com/celebrity/{id_}/awards/') as html_res:
                html_data = html_res.text
            soup = BeautifulSoup(html_data, 'lxml')
            content = soup.find('div', id='content')
            content_html = f'<h3>{content.h1.text}</h3>'
            soup_awards = content.find_all('div', class_="awards")
            for awards in soup_awards:
                awards_html = str(awards).replace('<div class="awards">', '').replace(
                    '<div class="hd">', '').replace('</div>', '').replace(
                    'h2', 'h4').replace('\n', '')
                content_html += awards_html
            page = await telegraph.create_page(actor_name, f'{info_html}{summary_html}{content_html}')
        else:
            page = await telegraph.create_page(actor_name, f'{info_html}{summary_html}')
        print('生成演员Instant View， URL:', page.url)

        return page.url

    try:
        url = loop.run_until_complete(main())
    finally:
        loop.run_until_complete(telegraph.close())

    return url


def subject_suggest(name):
    with utils.my_opener().get(
            f'https://movie.douban.com/j/subject_suggest?q={parse.quote(name)}') as html_data:
        json_data = ujson.loads(html_data.read().decode('utf-8'))
        suggest_result_list = list()
        for i in json_data:
            suggest_result = dict()
            if i['type'] == 'movie':
                suggest_result['type'] = 'movie'
                suggest_result['title'] = f'''{str(i['title'])}({str(i['year'])})'''
            elif i['type'] == 'celebrity':
                suggest_result['type'] = 'actor'
                suggest_result['title'] = str(i['title'])
            suggest_result['thumb_url'] = i['img']
            suggest_result['description'] = i['sub_title']
            suggest_result['id'] = i['id']
            suggest_result_list.append(suggest_result)
    return suggest_result_list


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
            comments_formatted += (str(comments_list[k])).strip()

        comments_with_punctuation = re.findall(han_pattern, comments_formatted)
        pure_comments = ''.join(comments_with_punctuation)

        return pure_comments

    async def download(url):
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(),
                                         headers=utils.head,
                                         cookies=utils.cookies) as session:
            html = await fetch(session, url)
            pure_comments = await parser(html)
            return pure_comments

    urls = [f'https://movie.douban.com/subject/{str(id_)}/comments?start={str(i * 20)}'
            f'&limit=20&sort=new_score&status=P' for i in range(11)]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    tasks = [asyncio.ensure_future(download(url)) for url in urls]
    loop.run_until_complete(asyncio.wait(tasks))

    all_final_comments = str()
    for task in tasks:
        all_final_comments += task.result()

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

    wordcloud = wordcloud.fit_words(dict(word_frequency_list))
    wordcloud.to_file(f"./img/{id_}.jpg")
