# twitter-bot-as-a-service

A lightweight Docker image written in Python 3 to post tweets as a service with AI models pretrained with [GPT-2](https://openai.com/blog/better-language-models/) based on Twitter data.
* Developing an automated twitter bot can be difficult, and time consuming due to the need to understand programming, AI tools, and back-end development
* This code included step-by-step directions to implement code that posts original tweets and replies to existing tweets
* Does not require time-consuming and costly training of AI models
* Includes multiple AI models trained on different personas (e.g., data journalists, Republicans, Democrats)
* Runs very inexpensively on Google Cloud's Cloud Run platform

## Setup

First, create a project in Google Cloud:
[TODO add steps to create a new project in Google Cloud]

Once you've created the project, clone this repository on your system:

```sh
git clone https://github.com/sdelgadoc/twitter-post-cloud-function
```

Then, make the new directory your working directory:
```sh
cd twitter-post-cloud-function
```

Build the Docker immage using the following command (this assumes you have Docker installed):
```sh
docker build -t post_tweet:latest .
```

Once the Docker image is built, tag the image to prepare for pushing to Google Cloud
```sh
docker tag post_tweet:latest gcr.io/[Google Cloud Project Name]/post_tweet
```

Then, create a new Cloud Run service:
[TODO add steps on how to create a Cloud Run service]
* Make sure to create it in us-central1 (Iowa) so it's easier to move data around

[TODO add the rest of the steps]

## Maintainer

Santiago Delgado  ([@santiagodc](https://twitter.com/santiagodc))
based on [download-tweets-ai-text-gen](https://github.com/minimaxir/download-tweets-ai-text-gen) by [@minimaxir](https://github.com/minimaxir)

## License

MIT

## Disclaimer

This repo has no affiliation with Twitter Inc.
