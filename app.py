from starlette.applications import Starlette
from starlette.responses import UJSONResponse
import uvicorn

import twint
from datetime import datetime
import logging
import en_core_web_sm
import os
import tweepy
from time import sleep
import json
import re

app = Starlette(debug=False)

# Needed to avoid cross-domain issues
response_header = {
    'Access-Control-Allow-Origin': '*'
}

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


@app.route('/', methods=['GET', 'POST', 'HEAD'])
async def homepage(request):
    
    if request.method == 'GET':
        params = request.query_params
        print("GET")
    elif request.method == 'POST':
        params = await request.json()
        print("POST")
    elif request.method == 'HEAD':
        print("HEAD")
        return UJSONResponse({'text': ''},
                             headers=response_header)
        
    print(params)
    
    return UJSONResponse({'text': "Hellow World"},
                         headers=response_header)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))