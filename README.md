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
git clone https://github.com/sdelgadoc/twitter-bot-as-a-service
```

Then, make the new directory your working directory:
```sh
cd twitter-bot-as-a-service
```

Build the Docker immage using the following command (this assumes you have Docker installed):
```sh
docker build -t post_tweet:latest .
```

Once the Docker image is built, tag the image to prepare for pushing to Google Cloud
```sh
docker tag post_tweet:latest gcr.io/[Google Cloud Project ID]/post_tweet
```
* _Note: [Google Cloud Project ID] is the ID of the Google Cloud Project we created earlier, in this case "post_tweet"_

Push the Docker image to your Google Cloud Container registry:
```sh
docker push gcr.io/[Google Cloud Project ID]/post_tweet
```

Then, create a new Cloud Run service:
* In the Google Cloud search bar type "cloud run"
* Select "Cloud Run" from the list of options
* In the Cloud Run configuration page, select CREATE SERVICE

In the Create Service configuration page:
* Set the Deployment platform as "Cloud Run (fully managed)"
* For Region, select "us-central1 (Iowa)"
  * This selection is surprisingly important because all the models are in that Region, and if you pick another one, it will degrade performance and increase cost
* For Service name, pick something relevant, in this case I will use "post-tweet"
* Finally for Authentication, select "Allow unauthenticated invocations"
  * You will likely want to get more rigorous with authentication, but for now, we're doing this quickly so we can see the result
* Click on NEXT to continue

In the Configure the service's first revision page:
* Select Deploy one revision from an existing image
* Click SELECT and search for the Docker container your pushed previously and select it
* Click on Show advanced setting
* Leave default values for everything except the following:
  * Set Memory Allocated to 4 GiB
  * Set Request timeout to 900
  * Set Maximum requests per container to 1

You are done!  Click on CREATE to create your Cloud Run service



## Maintainer

Santiago Delgado  ([@santiagodc](https://twitter.com/santiagodc))

## License

MIT

## Disclaimer

This repo has no affiliation with Twitter Inc.
