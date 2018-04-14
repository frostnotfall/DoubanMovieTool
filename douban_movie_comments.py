#!/usr/bin/env python3
# encoding: utf-8

import datetime
import re
from urllib import error

import jieba
import matplotlib as mpl
import numpy
import pandas
from bs4 import BeautifulSoup
from wordcloud import WordCloud

import util

mpl.use('Agg')
import matplotlib.pyplot as plt


def load():
    with util.my_opener().open('https://movie.douban.com/cinema/nowplaying/beijing/') as requrl:
        requrl_data = requrl.read().decode('utf-8')

    soup = BeautifulSoup(requrl_data, 'html.parser')
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


def get_comments(id_):

    def visit_url(url):
        try:
            with util.my_opener().open(url) as comment_url:
                comment_url_data = comment_url.read().decode('utf-8')

        except error.HTTPError as e:
            print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') + '：' +
                  '递归请求url：' + url + ' 出错，错误码：', e.code)
            return comments_all
        else:
            soup = BeautifulSoup(comment_url_data, 'html.parser')
            comment_data_list = soup.find_all('div', class_='comment')

            comments_list = []
            for item in comment_data_list:
                if item.find('p').string is not None:
                    comments_list.append(item.find('p').string)

            comments = ''
            for k in range(len(comments_list)):
                comments = comments + (str(comments_list[k])).strip()

            pattern = re.compile(r'[\u4e00-\u9fa5]+')
            filter_data = re.findall(pattern, comments)
            cleaned_comments = ''.join(filter_data)

            return cleaned_comments

    li = []
    for i in range(11):
        req_thread = util.MyThread(visit_url, args=('https://movie.douban.com/subject/' + id_ +
                                                    '/comments' + '?start=' + str(i * 20) +
                                                    '&limit=20&sort=new_score&status=P&percent_type=', ))
        li.append(req_thread)
        req_thread.start()

    comments_all = ''
    for t in li:
        t.join()

        comments_all += t.get_result()
    return comments_all


def save_img(id_):
    text = get_comments(id_)

    jieba.setLogLevel('ERROR')
    segment = jieba.lcut(text)
    word_df = pandas.DataFrame({'segment': segment})

    stopwords = pandas.read_csv("stopwords.txt", index_col=False,
                                quoting=3, sep="\t", names=['stopword'], encoding='utf-8')
    words_df = word_df[~word_df.segment.isin(stopwords.stopword)]

    words_stat = words_df.groupby(by=['segment'])['segment'].agg([numpy.size])\
        .rename(columns={"size": "计数"})
    words_stat = words_stat.reset_index().sort_values(by=["计数"], ascending=False)

    wordcloud = WordCloud(font_path="simhei.ttf",
                          background_color="white", max_font_size=80)
    word_frequence = {x[0]: x[1] for x in words_stat.head(1000).values}

    word_frequence_list = []
    for key in word_frequence:
        temp = (key, word_frequence[key])
        word_frequence_list.append(temp)

    mpl.rcParams['figure.figsize'] = (5.0, 2.5)
    try:
        wordcloud = wordcloud.fit_words(dict(word_frequence_list))
    except ValueError:
        print(datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S') +
              '：' + "电影ID：" + id_ + " 获取评论失败")
        return
    mpl.pyplot.imshow(wordcloud)
    mpl.pyplot.xticks([])
    mpl.pyplot.yticks([])
    mpl.pyplot.savefig("./img/" + id_ + ".jpg", dpi=300, bbox_inches='tight')
