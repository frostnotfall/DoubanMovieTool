#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import datetime
import json
import re
from urllib import parse

import aiohttp
import jieba
import numpy
import pandas
from aiograph import Telegraph
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
    movie_id_list = list()

    for i in coming_list.find_all('a'):
        movie_name = i.text
        movie_url = i.get('href').strip("//")
        movie_id = re.search(r"\d+", movie_url).group()
        movie_list.append(movie_name)
        movie_id_list.append('movie ' + movie_id)

    return movie_list, movie_id_list


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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegraph = Telegraph()

    async def main(id_):
        await telegraph.create_account('DoubanMovieTool')
        with util.my_opener().open('https://movie.douban.com/subject/{}/'.format(id_)) as html_res:
            html_data = html_res.read().decode('UTF-8')
        soup = BeautifulSoup(html_data, 'lxml')

        json_data = soup.find('script', type='application/ld+json').text
        try:
            json_data = json.loads(json_data)
            title = json_data['name']
            image_html = '<img src="' + json_data['image'] + '">'
            score = json_data['aggregateRating']['ratingValue']
        except json.decoder.JSONDecodeError:
            with util.my_opener().open('https://api.douban.com/v2/movie/subject/' +
                                       str(id_)) as html_data:
                json_data = json.load(html_data)
                title = json_data['title']
                image_html = '<img src="' + json_data['images']['small'] + '">'
                score = json_data['rating']['average']

        if score == '' or score == 0:
            score = '暂无评分'
        score_html = '<strong>评分：</strong>{}<br />'.format(score)

        info = soup.find('div', id='info')
        related_info = soup.find('div', class_='related-info')

        directors_html = '<strong>导演：</strong>' + str(info.find_all('a', rel="v:directedBy")).strip(
            '[|]') + '<br />'

        author_html = '<strong>编剧：</strong>' + str(
            info.find('span', text='编剧').next_sibling.next_sibling).replace('<span class="attrs">',
                                                                            '').replace('</span>',
                                                                                        '') + '<br />'

        actors_html = '<strong>主演：</strong>' + str(info.find_all('a', rel="v:starring")).strip(
            '[|]') + '<br />'

        genre_set = set()
        for genre in info.find_all('span', property="v:genre"):
            genre_set.add(genre.text)
        genre_html = '<strong>类型：</strong>' + ' / '.join(genre_set) + '<br/>'

        country_html = '<strong>制片国家/地区：</strong>' + str(
            info.find('span', text='制片国家/地区:').next_sibling).strip() + '<br />'

        language_html = '<strong>语言：</strong>' + str(
            info.find('span', text='语言:').next_sibling).strip() + '<br />'

        publish_date_set = set()
        for publish_date in info.find_all('span', property="v:initialReleaseDate"):
            publish_date_set.add(publish_date.text)
        publish_date_html = '<strong>上映日期：</strong>' + ' / '.join(publish_date_set) + '<br/>'

        aka_html = '<strong>又名：</strong>' + str(
            info.find('span', text='又名:').next_sibling).strip() + '<br />'

        imdb_html = '<strong>IMDb链接：</strong>' + str(
            info.find(href=re.compile(r"^http://www.imdb.com"))) + '<br />'

        try:
            summary = related_info.find('span', class_="all hidden").text.strip().replace(' ', '')
        except AttributeError:
            summary = related_info.find('span', property="v:summary").text.strip().replace(' ', '')

        summary_html = '<h3>{}:</h3><p>{}</p>'.format(related_info.h2.i.text, summary)

        info_html = image_html + '<h3>电影信息</h3>' + score_html + directors_html + author_html + \
                    actors_html + genre_html + country_html + language_html + publish_date_html + \
                    aka_html + imdb_html
        info_html = info_html.replace('/celebrity', 'https://movie.douban.com/celebrity')

        with util.my_opener().open(
                'https://movie.douban.com/subject/{}/awards/'.format(id_)) as html_res:
            html_data = html_res.read().decode('utf-8')
        soup = BeautifulSoup(html_data, 'lxml')
        content = soup.find('div', id='content')

        content_html = '<h3>{}：</h3>'.format(content.h1.text)

        for awards in content.find_all('div', class_="awards"):
            awards_div_h2 = awards.div.h2
            awards_href = awards_div_h2.a.get('href')
            awards_name = awards_div_h2.get_text().replace('\n', '')
            awards_name_html = '<br/><em><a href="{href}">{name}</a></em><br/>'.format(
                href=awards_href, name=awards_name)
            awards_html = str(awards.find_all('ul')).strip('[|]').replace(
                ', ', '').replace('<li></li>', '').replace('\n', '')
            content_html = content_html + awards_name_html + awards_html

        page = await telegraph.create_page(title, info_html + summary_html + content_html)
        print('生成Instant View， URL:', page.url)
        return page.url, score

    try:
        url, score = loop.run_until_complete(main(id_))
    finally:
        loop.run_until_complete(telegraph.close())

    return url, score


def actor_info(id_):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegraph = Telegraph()

    async def main():
        await telegraph.create_account('DoubanMovieTool')
        with util.my_opener().open(
                'https://movie.douban.com/celebrity/{id}/'.format(id=id_)) as html_res:
            html_data = html_res.read().decode('UTF-8')

        soup = BeautifulSoup(html_data, 'lxml')
        headline = soup.find('div', id='headline', class_="item")
        actor_name = headline.find('div', class_="pic").find('a', class_="nbg").get('title')
        image_url = headline.find('div', class_="pic").find('a', class_="nbg").get('href')
        image_html = '<img src="{}">'.format(image_url)

        ul = headline.find('ul', class_="")
        ul_html = str(ul).replace('span', 'strong').replace('\n', '').replace('  ', '')

        info_html = image_html + '<h3>影人信息</h3>' + ul_html

        intro = soup.find('div', id="intro")
        try:
            summary = intro.find('span', class_="all hidden").text.strip().replace(' ', '')
        except AttributeError:
            summary = intro.find('div', class_="bd").text.strip().replace(' ', '')

        summary_html = '<h3>影人简介:</h3><p>{}</p>'.format(summary)

        with util.my_opener().open(
                'https://movie.douban.com/celebrity/{id}/awards/'.format(id=id_)) as html_res:
            html_data = html_res.read().decode('utf-8')
        soup = BeautifulSoup(html_data, 'lxml')
        content = soup.find('div', id='content')

        content_html = '<h3>{}</h3>'.format(content.h1.text)

        for awards in content.find_all('div', class_="awards"):
            awards_html = str(awards).replace('<div class="awards">', '').replace(
                '<div class="hd">', '').replace('</div>', '').replace(
                'h2', 'h4').replace('\n', '')
            content_html = content_html + awards_html

        page = await telegraph.create_page(actor_name, info_html + summary_html + content_html)
        print('生成Instant View， URL:', page.url)
        return page.url

    try:
        url = loop.run_until_complete(main())
    finally:
        loop.run_until_complete(telegraph.close())

    return url


def subject_suggest(name):
    with util.my_opener().open(
            'https://movie.douban.com/j/subject_suggest?q={}'.format(parse.quote(name))) as html_data:
        json_data = json.loads(html_data.read().decode('utf-8'))
        suggest_result_list = list()
        for i in json_data:
            suggest_result = dict()
            if i['type'] == 'movie':
                suggest_result['type'] = 'movie'
                suggest_result['title'] = str(i['title']) + '(' + str(i['year']) + ')'
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
            comments_formatted = comments_formatted + (str(comments_list[k])).strip()

        # \u4e00-\u9fa5 Unicode汉字编码范围
        pattern = re.compile(r'[\u4e00-\u9fa5]+')
        comments_with_punctuation = re.findall(pattern, comments_formatted)
        pure_comments = ''.join(comments_with_punctuation)

        return pure_comments

    async def download(url):
        html = await fetch(session, url)
        pure_comments = await parser(html)
        return pure_comments

    urls = ['https://movie.douban.com/subject/' + str(id_) + '/comments?start=' + str(
        i * 20) + '&limit=20&sort=new_score&status=P'.format(i) for i in range(11)]

    session = util.my_session()
    loop = asyncio.get_event_loop()
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


def instant_view():
    import asyncio
    from aiograph import Telegraph

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegraph = Telegraph()

    async def main():
        await telegraph.create_account('DoubanMovieTool')
        with util.my_opener().open('https://movie.douban.com/subject/26266893/') as html_res:
            html_data = html_res.read().decode('UTF-8')
        soup = BeautifulSoup(html_data, 'lxml')

        json_data = soup.find('script', type='application/ld+json').text
        dict = json.loads(json_data)
        title = dict['name']
        image_html = '<img src="' + dict['image'] + '">'
        score = dict['aggregateRating']['scoreValue']
        score_html = '<strong>评分：{}</strong><br />'.format(score)

        info = soup.find('div', id='info')
        related_info = soup.find('div', class_='related-info')

        directors_html = '<strong>导演：</strong>' + str(info.find_all('a', rel="v:directedBy")).strip(
            '[|]') + '<br />'

        author_html = '<strong>编剧：</strong>' + str(
            info.find('span', text='编剧').next_sibling.next_sibling).replace('<span class="attrs">',
                                                                            '').replace('</span>',
                                                                                        '') + '<br />'
        actors_html = '<strong>主演：</strong>' + str(info.find_all('a', rel="v:starring")).strip(
            '[|]') + '<br />'

        genre_set = set()
        for genre in info.find_all('span', property="v:genre"):
            genre_set.add(genre.text)
        genre_html = '<strong>类型：</strong>' + ' / '.join(genre_set) + '<br/>'

        country_html = '<strong>制片国家/地区：</strong>' + str(
            info.find('span', text='制片国家/地区:').next_sibling).strip() + '<br />'

        language_html = '<strong>语言：</strong>' + str(
            info.find('span', text='语言:').next_sibling).strip() + '<br />'

        publish_date_set = set()
        for publish_date in info.find_all('span', property="v:initialReleaseDate"):
            publish_date_set.add(publish_date.text)
        publish_date_html = '<strong>上映日期：</strong>' + ' / '.join(publish_date_set) + '<br/>'

        aka_html = '<strong>又名：</strong>' + str(
            info.find('span', text='又名:').next_sibling).strip() + '<br />'

        imdb_html = '<strong>IMDb链接：</strong>' + str(
            info.find(href=re.compile(r"^http://www.imdb.com"))) + '<br />'

        try:
            summary = related_info.find('span', class_="all hidden").text.strip().replace(' ', '')
        except AttributeError:
            summary = related_info.find('span', property="v:summary").text.strip().replace(' ', '')

        summary_html = '<br /><strong>{}:</strong><br />{}<br /><br/>'.format(related_info.h2.i.text,
                                                                              summary)

        info_html = image_html + score_html + directors_html + author_html + actors_html + \
                    genre_html + country_html + language_html + publish_date_html + aka_html + \
                    imdb_html + summary_html

        with util.my_opener().open('https://movie.douban.com/subject/26266893/awards/') as html_res:
            html_data = html_res.read().decode('utf-8')
        soup = BeautifulSoup(html_data, 'lxml')
        content = soup.find('div', id='content')

        content_html = '<strong>{}</strong><br/>'.format(content.h1.text)

        for awards in content.find_all('div', class_="awards"):
            awards_div_h2 = awards.div.h2
            awards_href = awards_div_h2.a.get('href')
            awards_name = awards_div_h2.get_text().replace('\n', '')
            awards_name_html = '<br/><em><a href="{href}">{name}</a></em><br/>'.format(
                href=awards_href, name=awards_name)
            awards_html = str(awards.find_all('ul')).strip('[|]').replace(
                ', ', '').replace('<li></li>', '').replace('\n', '')
            content_html = content_html + awards_name_html + awards_html

        page = await telegraph.create_page(title, info_html + content_html)
        print('生成Instant View， URL:', page.url)
        return page.url

    try:
        return_value = loop.run_until_complete(main())
    finally:
        loop.run_until_complete(telegraph.close())

    return return_value
