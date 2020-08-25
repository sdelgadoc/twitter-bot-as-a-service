from flask import Flask
from flask import request
import asyncio

import twint
from datetime import datetime
import logging
import os
import tweepy
from time import sleep
import json
import re
from google.cloud import storage
import gc

app = Flask(__name__)


def clean_text(tweet_text, strip_usertags = False, strip_hashtags = False):
    """
    Remove sections of the tweet text (clean) based on parameters
    :param tweet_text: Text for which sentiment should be measured
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    """
    
    # Strip all the leading usertags
    while re.search(r"^@[a-zA-Z0-9_]+", tweet_text):
        tweet_text = re.sub(r"^@[a-zA-Z0-9_]+", '', tweet_text).strip()

    # Regex pattern for removing URL's
    pattern = r"http\S+|pic\.\S+|\xa0|…"
    
    if strip_usertags:
        pattern += r"|@[a-zA-Z0-9_]+"
    
    if strip_hashtags:
        pattern += r"|#[a-zA-Z0-9_]+"
    
    tweet_text = re.sub(pattern, '', tweet_text).strip()
    
    return tweet_text

def is_statement(tweet_text, nlp):
    """
    Determines if the tweet is a self contained statement
    :param tweet_text: The tweet's text
    :param nlp: A spaCy object
    """

    # Get the first sentence in the tweet text
    doc = nlp(tweet_text)
    # Create an array of sentence strings
    sentences = [sent.string.strip() for sent in doc.sents]

    # Process the first sentence in the tweet
    doc = nlp(sentences[0])
    
    ## Rule: If the subject is a person, place or thing then pass
    for token in doc:
        if token.dep_ == "nsubj":
            if token.pos_ == "NOUN" or token.pos_ == "PROPN":
                return 1
    
    ## Rule: If the subject is a personal pronoun, then pass
    for token in doc:
        if token.dep_ == "nsubj":
            if token.text.lower() == "I" or token.text.lower() == "me" or token.text.lower() == "we" or token.text.lower() == "us": 
                return 2
    
    ## Rule: If the first word is a conjunction, then fail
    # Find the first token in the sentencce that is not punctuation
    for i, token in enumerate(doc):
        if token.pos_ != "PUNCT": break
            
    # If the first non-punctuoation token is a conjunction
    if doc[i].pos_ == "CCONJ" or doc[0].pos_ == "CONJ":
        return -1
    
    ## Rule: If the tweet starts with a dependent clause, then fail
    # Find the first token in the sentencce that is not punctuation
    for i, token in enumerate(doc):
        if token.pos_ != "PUNCT": break
    
    # Initialize flags for finding commas and subject to false
    comma_found = False
    # Iterate through sentence to find if a comma occurs before the subject
    for j, token in enumerate(doc):
        # If the token is not an initial punctuation
        if j >= i:
            if token.text == ",": comma_found = True
            
            # If the subject is found after a comman, set filter to -1
            if token.dep_ == "nsubj" and comma_found == True:
                return -2
        
    ## Rule: If any of the objects of the sentence are pronouns, the fail
    for token in doc:
        if token.dep_ == "dobj" or token.dep_ == "obj":
            if token.pos_ != "PRON":
                return -3
    
    ## Rule: If any of the sentence's subjects are pronouns or determiners,
    ##       then fail
    for token in doc:
        if token.dep_ == "nsubj" or token.dep_ == "nsubjpass":
            if token.pos_ == "PRON" or token.pos_ == "DET":
                return -4
    
    return 0


def is_reply(tweet):
    """
    Determines if the tweet is a reply to another tweet.
    :param tweet: Twint tweet object whose object will be formated
    """

    # A reply's conversation_id is different than the id_str
    if tweet.conversation_id != tweet.id_str:
        return True

    # If not a reply to another user, there will only be 1 entry in reply_to
    if len(tweet.reply_to) == 1:
        return False

    # Check to see if any of the other users "replied" are in the tweet text
    users = tweet.reply_to[1:]
    conversations = [user["username"].lower() in tweet.tweet.lower() for user in users]

    # If any if the usernames are not present in text, then it must be a reply
    if sum(conversations) < len(users):
        return True
    
    # On older tweets, tweets starting with an "@" are de-facto replies
    if tweet.tweet.startswith('@'):
        return True
        
    return False


@app.route('/', methods=['GET', 'POST'])
def main():
    
    import en_core_web_sm
    
    ## Process function parameters    
    # If the function was run as an http function
    if hasattr(request, 'headers'):
        content_type = request.headers['Content-Type']
        
        if content_type == 'application/json':
            params = request.get_json()
        elif content_type == 'application/octet-stream':
            params = json.loads(request.data)
    # If the function is run from coomand line run as a python function
    else:
        params = json.loads(request)
    
    
    usernames = params['usernames']
    tweet_type = params['tweet_type']
    model = params['model']


    ## Constants
    # Count of user tweets to process
    tweets_to_process = 10
    # Twitter API delay (seconds)
    tweepy_delay = 1.5
    # Times to retry generating a tweet
    generate_retries = 5
    
    
    # Surpress random twint warnings
    logger = logging.getLogger()
    logger.disabled = True
    
    
    # Get Twitter API authentication data
    keys = {}
    keys['consumer_key'] = os.environ['CONSUMER_KEY']
    keys['access_token'] = os.environ['ACCESS_TOKEN']
    keys['access_token_secret'] = os.environ['ACCESS_TOKEN_SECRET']
    keys['consumer_secret'] = os.environ['CONSUMER_SECRET']
    
    # Authenticate with the Twitter API
    auth = tweepy.OAuthHandler(keys["consumer_key"], keys["consumer_secret"])
    auth.set_access_token(keys["access_token"], keys["access_token_secret"])
    api = tweepy.API(auth)
    
    # Download the model
    bucket_name = 'tweets-ai-text-gen-plus-models'
    prefix = model + '/'
    root_folder = '/tmp'
    path = os.path.join(root_folder, prefix)
    
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")
    
    # Array of downloaded file names
    files = []
    # Create the folder to save files if it doesn't exist
    if not os.path.exists(path):
        os.makedirs(path)
    # Iterate through file list and download
    for blob in blobs:
        # If the blob is not a folder, download the file
        filename = blob.name.split('/')[-1]
        if not os.path.exists(path + filename):
            blob.download_to_filename(path + filename)
            files.insert(0,path + filename)
    
    # Create the natural language processing object to be used in many cases
    nlp = en_core_web_sm.load()
    
    # The tweet that will be posted
    tweet = ""
    
    if tweet_type.lower() == "original".lower():
        import gpt_2_simple as gpt2
        import tensorflow as tf
        
        # Set the source user's username
        username = usernames[0]
        
        # Collect the latest tweets from the authenticating user
        tweet_data = []
        c = twint.Config()
        c.Store_object = True
        c.Hide_output = True
        c.Username = username
        c.Limit = tweets_to_process
        c.Store_object_tweets_list = tweet_data
    
        asyncio.set_event_loop(asyncio.new_event_loop())
        twint.run.Search(c)
        
        print("Collected tweets from source username: " + username)
        
        
        # Find latest tweet that is not a reply, and use as word seed generator
        word_seed = ""
        for tweet in tweet_data:
            if not is_reply(tweet):
                word_seed = tweet.tweet.split()
                word_seed = word_seed[0]
                break
        
        # Clean up collected tweet data before loading Tensorflow
        tweet_data = []
        gc.collect()
        
        # Generate the tweet using the gpt-2 model
        sess = gpt2.start_tf_sess()
        gpt2.load_gpt2(sess, run_name = model, checkpoint_dir = root_folder)
        
        prefix = "****ARGUMENTS\nORIGINAL\n****PARENT\n" + "****IN_REPLY_TO\n"
        prefix += "****TWEET\n" + word_seed
        
        tweets = gpt2.generate(sess,
                              run_name=model,
                              checkpoint_dir=root_folder,
                              length=140,
                              temperature=.7,
                              nsamples=generate_retries,
                              batch_size=1,
                              prefix=prefix,
                              truncate='<|endoftext|>',
                              include_prefix=False,
                              return_as_list=True
                             )
        
        
        # Iterate through generated tweets and select the first statement
        tweet = ""
        for tweet in tweets:
            if is_statement(tweet, nlp):
                break
        
        tweet = word_seed + tweet
        
        # Post the tweet
        api.update_status(tweet)

        
        # Clean up memory as much as possible
        sess.close()
        tf.reset_default_graph()
        nlp = []
        gc.collect()
        
        
    elif tweet_type.lower() == "reply".lower():
        import gpt_2_simple as gpt2
        import tensorflow as tf
        
        # Set the authenticating user's username
        username = api.me().screen_name
        sleep(tweepy_delay)
        
        # Collect the latest tweets from the authenticating user
        tweet_data = []
        c = twint.Config()
        c.Store_object = True
        c.Hide_output = True
        c.Username = username
        c.Limit = tweets_to_process
        c.Store_object_tweets_list = tweet_data
    
        asyncio.set_event_loop(asyncio.new_event_loop())
        twint.run.Search(c)
        
        print("Collected tweets from calling username: " + username)
        
        # Create a list of tweets that were replied-to
        replied_to_tweets = []
        for tweet in tweet_data:
            
            # If the tweet is a reply, append the tweet ID it replied-to
            if is_reply(tweet):
                try:
                    # Get the tweet's API object
                    tweet_object = api.get_status(tweet.id_str)
                    sleep(tweepy_delay)
                
                    # Append the tweet ID that was replied-to
                    replied_to_tweets.append(tweet_object.in_reply_to_status_id_str)
                
                # If tweet doesn't exist, ignore it
                except tweepy.error.TweepError:
                    pass
        
        tweet_data = []
        # Create an array for the target user's tweets
        target_tweet_data = []
        
        for username in usernames:
        
            c = twint.Config()
            c.Store_object = True
            c.Hide_output = True
            c.Username = username
            c.Limit = tweets_to_process
            c.Store_object_tweets_list = tweet_data
        
            asyncio.set_event_loop(asyncio.new_event_loop())
            twint.run.Search(c)
            
            for tweet in tweet_data:
                
                if not is_reply(tweet) and is_statement(tweet.tweet, nlp) > 0 and not tweet.id_str in replied_to_tweets:
                    
                    target_tweet_data.append(tweet)
            
            print("Collected tweets from target username: " + username)
        
        # Sort the potential target tweets by most recent to least recent
        target_tweet_data.sort(key=lambda x: x.datetime, reverse = True)
        
        # Clean the tweet text for model input
        target_tweet_text = clean_text(target_tweet_data[0].tweet)
        
        # Generate the tweet using the gpt-2 model
        sess = gpt2.start_tf_sess()
        gpt2.load_gpt2(sess, run_name = model, checkpoint_dir = root_folder)
        
        prefix = "****ARGUMENTS\nREPLY\n****PARENT\n" + target_tweet_text + "\n"
        prefix += "****IN_REPLY_TO\n" + target_tweet_text + "\n****TWEET\n"
        
        tweet = gpt2.generate(sess,
                              run_name=model,
                              checkpoint_dir=root_folder,
                              length=140,
                              temperature=.7,
                              nsamples=1,
                              batch_size=1,
                              prefix=prefix,
                              truncate='<|endoftext|>',
                              include_prefix=False,
                              return_as_list=True
                             )[0]
        
        # Post the tweet
        api.update_status("@" + target_tweet_data[0].username + " " + tweet, 
                          target_tweet_data[0].id_str)
      
        
        # Clean up memory as much as possible
        sess.close()
        tf.reset_default_graph()
        tweet_data = []
        nlp = []
        gc.collect()
    
    
    # Delete stored files and directory
    for file in files:
        if not os.path.isdir(file):
            os.remove(file)
    
    os.rmdir(path)
    
    # Run garbage collection one last time for good measure
    gc.collect()
    
    print("Posted the following tweet: " + tweet)
    return("Posted the following tweet: " + tweet)
        

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))