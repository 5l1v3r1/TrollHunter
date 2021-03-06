import pandas as pd
import numpy as np
import math
import os
from Sentiment import get_sentiment_value, get_polarity_value, get_subjectivity_value
from Keyword import extract_v2, filter_text_by_pos, lemetize_text
from Utils import cleantext
import warnings
from nltk import word_tokenize
from gensim import corpora, models, similarities

warnings.simplefilter(action='ignore')

class Indicator:
    def __init__(self, data_folder):
        self.data_folder = data_folder

    @staticmethod
    def average(values_tab):
        return sum(values_tab) / len(values_tab)

    @staticmethod
    def get_mean_time_gap(tweets):
        len_t = len(tweets)
        if len_t <= 1:
            return 0

        before = tweets[0]
        cumul = 0
        for i in range(1, len_t):
            current = tweets[i]
            cumul += current - before
            before = current

        return cumul / len_t

    @staticmethod
    def nb_different_topics(texts):
        textValues = texts.values
        texts = texts.apply(cleantext)
        keywords_column = texts.apply(lambda x: extract_v2(x, withNumbers=False))
        values = keywords_column.values
        list_sets = []

        topics = []
        i = 0
        for keywords in values:
            to_remove = []
            new_kws = set(" ".join(keywords).split())

            j = 0
            for one_set in list_sets:
                inter = one_set.intersection(new_kws)
                if len(inter) > 0:
                    to_remove.append(j)
                j += 1

            if len(to_remove) > 0:
                new_set = set().union(new_kws)
                new_topic = []
                for j in to_remove:
                    one_set = list_sets[j]
                    new_set = new_set.union(one_set)
                    for topic in topics[j]:
                        new_topic.append(topic)

                new_topics = []
                new_list_sets = []
                for j in range(0, len(list_sets)):
                    if j not in to_remove:
                        new_topics.append(topics[j])
                        new_list_sets.append(list_sets[j])

                topics = new_topics
                list_sets = new_list_sets

                list_sets.append(new_set)
                topics.append(new_topic)

            elif len(new_kws) > 0:
                list_sets.append(new_kws)
                topics.append([textValues[i]])

            i += 1

        #file = open(name, 'w')
        #for topic in topics:
        #    for text in topic:
        #        file.write(text+"\n")
        #    file.write('--------------------\n')

        #file.close()
        return len(list_sets)

    @staticmethod
    def nb_different_topics_v2(name, texts):
        textValues = texts.values
        texts = texts.apply(cleantext)
        lemmetized_column = texts.apply(lambda x: lemetize_text(x))
        values = lemmetized_column.values
        list_sets = []

        topics = []

        tab_texts = [word_tokenize(text) for text in values]
        dictionary = corpora.Dictionary(tab_texts)
        feature_cnt = len(dictionary.token2id)
        corpus = [dictionary.doc2bow(text) for text in tab_texts]
        tfidf = models.TfidfModel(corpus)

        for keyword in values:
            kw_vector = dictionary.doc2bow(word_tokenize(keyword))
            index = similarities.SparseMatrixSimilarity(tfidf[corpus], num_features=feature_cnt)
            sim = index[tfidf[kw_vector]]
            for i in range(len(sim)):
                print('keyword is similar to text%d: %.2f' % (i + 1, sim[i]))


        return 0

    @staticmethod
    def get_indicators_user(user_file):
        df_csv = pd.read_csv(user_file)

        tweet_list = df_csv[["text"]]
        tweet_list['text'] = tweet_list['text'].apply(str)

        tweet_list['sentiment'] = tweet_list['text'].apply(get_sentiment_value)
        tweet_list['polarity'] = tweet_list['text'].apply(get_polarity_value)
        tweet_list['subjectivity'] = tweet_list['text'].apply(get_subjectivity_value)

        average_sentiment = tweet_list['sentiment'].mean()
        average_polarity = tweet_list['polarity'].mean()
        average_subjectivity = tweet_list['subjectivity'].mean()
        average_post_time_gap = Indicator.get_mean_time_gap(df_csv['created_at'].values) / 1000 / 60
        if math.isnan(average_post_time_gap) is True:
            average_post_time_gap = 0

        nb_topics = Indicator.nb_different_topics(tweet_list['text'])
        print(user_file)

        return average_sentiment, average_polarity, average_subjectivity, average_post_time_gap, nb_topics, tweet_list['text'].size

    def get_all_indicator_users(self):
        average_sentiment = []
        average_polarity = []
        average_subjectivity = []
        average_time_gap = []
        average_nb_topics = []

        out = pd.DataFrame(columns=['sentiment', 'polarity', 'subjectivity', 'timegap', 'nb_topics', 'nb_tweets'])

        cpt = 1
        for element in os.listdir(self.data_folder):
            if not os.path.isdir(element):
                sentiment, polarity, subjectivity, time_gap, nb_topics, nb_tweets = self.get_indicators_user(os.path.join(self.data_folder, element))
                row = pd.DataFrame(np.array([[sentiment, polarity, subjectivity, time_gap, nb_topics, nb_tweets]]),
                                   columns=['sentiment', 'polarity', 'subjectivity', 'timegap', 'nb_topics', 'nb_tweets'])
                out = pd.concat([out, row], ignore_index=True)

                average_sentiment.append(sentiment)
                average_polarity.append(polarity)
                average_subjectivity.append(subjectivity)
                average_time_gap.append(time_gap)
                average_nb_topics.append(nb_topics)

                cpt += 1

        out.to_csv(self.data_folder+".csv", index=False)

        average_sentiment = self.average(average_sentiment)
        average_polarity = self.average(average_polarity)
        average_subjectivity = self.average(average_subjectivity)

        average_time_gap = np.array(average_time_gap)
        average_time_gap_no_zero = average_time_gap[average_time_gap != 0.0]
        average_time_gap = self.average(average_time_gap_no_zero)

        average_nb_topics = self.average(average_nb_topics)

        return average_sentiment, average_polarity, average_subjectivity, average_time_gap, average_nb_topics


if __name__ == '__main__':
    indi = Indicator('./example/troll-user-tweets')
    print(indi.get_all_indicator_users())
    indi = Indicator('./example/nontroll-user-tweets')
    print(indi.get_all_indicator_users())
