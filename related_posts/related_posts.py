"""
Related posts plugin for Pelican
================================

Adds related_posts variable to article's context
"""

from bs4 import BeautifulSoup
from pelican import signals
from gensim import corpora, models, similarities
import os
from nltk.tokenize import RegexpTokenizer
import nltk
from collections import defaultdict
from pprint import pprint


def filter_dictionary(raw_dictionary,
                      stop_words=nltk.corpus.stopwords.words('english'),
                      min_count=2):
    stop_ids = [raw_dictionary.token2id[word] for word in stop_words
                if word in raw_dictionary.token2id]
    print 'a' in raw_dictionary
    rare_ids = [id for id, freq in raw_dictionary.dfs.iteritems()
                    if freq < min_count]
    raw_dictionary.filter_tokens(stop_ids + rare_ids)
    raw_dictionary.compactify()
    return raw_dictionary

def recommend_articles(articles):
    tokenizer = RegexpTokenizer(r'\w+')
    documents = [tokenizer.tokenize(BeautifulSoup(article.content).get_text().lower())
                 for article in articles]
    fnames = [article.source_path for article in articles]
    dictionary = corpora.Dictionary(documents)
    dictionary = filter_dictionary(dictionary)
    corpus = [dictionary.doc2bow(doc) for doc in documents]
    lsi = models.LsiModel(corpus, id2word=dictionary, num_topics=5)
    index = similarities.MatrixSimilarity(lsi[corpus])
    for topic in lsi.print_topics():
        print topic
    fname_scores = defaultdict(list)
    for fname, sims in zip(fnames, index):
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        for id, score in sims:
            if fname == fnames[id]:
                continue
            fname_scores[os.path.abspath(fname)].append(
                (os.path.abspath(fnames[id]), score)
            )
    return fname_scores


def add_related_posts(generator):
    fname_scores = recommend_articles(generator.articles)
    numentries = 5
    articles_by_path = {art.source_path: art for art in generator.articles}
    for article in generator.articles:
        article.score = {}
    for article in generator.articles:
        related_posts = sorted(fname_scores[article.source_path], key=lambda x: -x[1])
        posts = []
        for i, entry in enumerate(related_posts):
            if i >= numentries:
                break
            source_path, similarity = entry
            try:
                art = articles_by_path[source_path]
                article.score[unicode(art.source_path)] = similarity
            except KeyError:
                print "can't find article {}".format(source_path)
            posts.append(art)
        article.related_posts = posts

def register():
    signals.article_generator_finalized.connect(add_related_posts)