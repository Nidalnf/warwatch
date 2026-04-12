from flask import Flask, jsonify
import feedparser
import requests
import json
import sqlite3
import os
from datetime import datetime, timedelta
from collections import Counter
import re

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

FEEDS = {
    # Iran
    'tehrantimes':      { 'url': 'https://www.tehrantimes.com/rss',                             'region': 'iran' },
    'presstv':          { 'url': 'https://www.presstv.ir/rss.xml',                              'region': 'iran' },
    'iranintl':         { 'url': 'https://www.iranintl.com/en/rss.xml',                         'region': 'iran' },
    'bbc_iran':         { 'url': 'https://feeds.bbci.co.uk/persian/rss.xml',                    'region': 'iran' },
    'cnn_iran':         { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'iran' },
    'aljazeera_iran':   { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'iran' },

    # USA
    'voa':              { 'url': 'https://www.voanews.com/api/zmpq$_eqiez',                     'region': 'usa' },
    'nyt':              { 'url': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',      'region': 'usa' },
    'wapo':             { 'url': 'https://feeds.washingtonpost.com/rss/world',                  'region': 'usa' },
    'theintercept':     { 'url': 'https://theintercept.com/feed/?rss',                          'region': 'usa' },
    'democracynow':     { 'url': 'https://www.democracynow.org/democracynow.rss',               'region': 'usa' },
    'cnn_usa':          { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'usa' },
    'aljazeera_usa':    { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'usa' },

    # Israel
    'jpost':            { 'url': 'https://www.jpost.com/Rss/RssFeedsHeadlines.aspx',           'region': 'israel' },
    'timesofisrael':    { 'url': 'https://www.timesofisrael.com/feed/',                         'region': 'israel' },
    '972mag':           { 'url': 'https://www.972mag.com/feed/',                                'region': 'israel' },
    'bbc_israel':       { 'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',                 'region': 'israel' },
    'cnn_israel':       { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'israel' },
    'aljazeera_israel': { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'israel' },

    # Palestine
    'middleeasteye':    { 'url': 'https://www.middleeasteye.net/rss',                           'region': 'palestine' },
    'mondoweiss':       { 'url': 'https://mondoweiss.net/feed/',                                'region': 'palestine' },
    'bbc_palestine':    { 'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',                 'region': 'palestine' },
    'cnn_palestine':    { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'palestine' },
    'aljazeera_pal':    { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'palestine' },

    # India
    'ddnews':           { 'url': 'https://ddnews.gov.in/feed/',                                 'region': 'india' },
    'ndtv':             { 'url': 'https://feeds.feedburner.com/ndtvnews-top-stories',           'region': 'india' },
    'republic':         { 'url': 'https://www.republicworld.com/rss/india-news.xml',            'region': 'india' },
    'timesnow':         { 'url': 'https://www.timesnownews.com/rss/india.xml',                  'region': 'india' },
    'opindia':          { 'url': 'https://www.opindia.com/feed/',                               'region': 'india' },
    'thewire':          { 'url': 'https://thewire.in/feed',                                     'region': 'india' },
    'scroll':           { 'url': 'https://scroll.in/feed',                                      'region': 'india' },
    'bbc_india':        { 'url': 'https://feeds.bbci.co.uk/news/world/asia/rss.xml',            'region': 'india' },
    'cnn_india':        { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'india' },
    'aljazeera_india':  { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'india' },

    # Pakistan
    'radiopakistan':    { 'url': 'https://www.radio.gov.pk/rss',                                'region': 'pakistan' },
    'dawn':             { 'url': 'https://www.dawn.com/feeds/home',                             'region': 'pakistan' },
    'geo':              { 'url': 'https://www.geo.tv/rss/1/0',                                  'region': 'pakistan' },
    'ary':              { 'url': 'https://arynews.tv/feed/',                                    'region': 'pakistan' },
    'bbc_pakistan':     { 'url': 'https://feeds.bbci.co.uk/news/world/asia/rss.xml',            'region': 'pakistan' },
    'cnn_pakistan':     { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'pakistan' },
    'aljazeera_pak':    { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'pakistan' },

    # Russia
    'tass':             { 'url': 'https://tass.com/rss/v2.xml',                                 'region': 'russia' },
    'rt':               { 'url': 'https://www.rt.com/rss/news/',                                'region': 'russia' },
    'bbc_russia':       { 'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',                 'region': 'russia' },
    'cnn_russia':       { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                    'region': 'russia' },
    'aljazeera_russia': { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                   'region': 'russia' },
    'dw':               { 'url': 'https://rss.dw.com/rdf/rss-en-all',                          'region': 'russia' },

    # Ukraine
    'kyiv_independent': { 'url': 'https://kyivindependent.com/feed/',                          'region': 'ukraine' },
    'ukr_pravda':       { 'url': 'https://www.pravda.com.ua/eng/rss/view_news/',               'region': 'ukraine' },
    'bbc_ukraine':      { 'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',                'region': 'ukraine' },
    'cnn_ukraine':      { 'url': 'http://rss.cnn.com/rss/edition_world.rss',                   'region': 'ukraine' },
    'aljazeera_ukr':    { 'url': 'https://www.aljazeera.com/xml/rss/all.xml',                  'region': 'ukraine' },
}

STOPWORDS = set([
    'the','a','an','and','or','but','in','on','at','to','for','of','with',
    'is','are','was','were','be','been','being','have','has','had','do',
    'does','did','will','would','could','should','may','might','shall',
    'that','this','these','those','it','its','by','from','as','up','about',
    'into','through','during','before','after','above','below','between',
    'out','off','over','under','again','then','once','here','there','when',
    'where','why','how','all','both','each','few','more','most','other',
    'some','such','no','not','only','own','same','so','than','too','very',
    'just','say','says','said','new','us','can','after','also','back',
    'his','her','their','our','your','my','he','she','they','we','who',
    'what','which','i','you','him','them','its','s','t','re','ve','ll',
    'two','one','three','four','five','six','seven','eight','nine','ten',
])

DB_PATH = 'headlines.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS headlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT,
            region TEXT,
            title TEXT,
            link TEXT,
            fetched_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_headlines(source_id, region, articles):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    for article in articles:
        if article.get('title'):
            c.execute(
                'INSERT INTO headlines (source_id, region, title, link, fetched_at) VALUES (?, ?, ?, ?, ?)',
                (source_id, region, article['title'], article.get('link',''), now)
            )
    conn.commit()
    conn.close()

def get_word_counts(region, days=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    c.execute(
        'SELECT source_id, title FROM headlines WHERE region=? AND fetched_at > ?',
        (region, since)
    )
    rows = c.fetchall()
    conn.close()

    by_source = {}
    for source_id, title in rows:
        if source_id not in by_source:
            by_source[source_id] = []
        words = re.findall(r'\b[a-z]+\b', title.lower())
        filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
        by_source[source_id].extend(filtered)

    result = {}
    for source_id, words in by_source.items():
        counter = Counter(words)
        result[source_id] = counter.most_common(20)

    return result

def fetch_feed(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        articles = []
        for entry in feed.entries[:8]:
            articles.append({
                'title': entry.get('title', ''),
                'link':  entry.get('link', ''),
                'date':  entry.get('published', ''),
            })
        return articles
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return []

@app.route('/feeds/<region>')
def get_feeds(region):
    results = {}
    for source_id, info in FEEDS.items():
        if info['region'] == region:
            articles = fetch_feed(info['url'])
            if articles:
                save_headlines(source_id, region, articles)
            results[source_id] = articles
    return jsonify(results)

@app.route('/analysis/<region>')
def get_analysis(region):
    today = get_word_counts(region, days=1)
    week = get_word_counts(region, days=7)
    return jsonify({'today': today, 'week': week})

@app.route('/outlets')
def get_outlets():
    with open('outlets.json', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/')
def home():
    return open('index.html', encoding='utf-8').read()

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)