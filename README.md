# twitter-bot-as-a-service

A lightweight Docker image written in Python 3 to post tweets as a service with AI models pretrained with [GPT-2](https://openai.com/blog/better-language-models/) based on Twitter data

For live examples of the code, check out [Human data journalist](https://twitter.com/datajourno_gpt2), [Republican reading the news](https://twitter.com/apGOP_gpt2), and [Democrat reading the news](https://twitter.com/apDNC_gpt2)

* Repo included step-by-step directions to implement a Docker image on Google Cloud Run that posts original tweets and replies to existing tweets
* Does not require time-consuming and costly training of AI models
* Includes multiple AI models trained on different personas (e.g., data journalists, Republicans, Democrats)
* Runs very inexpensively on Google Cloud's Cloud Run platform

## Setup

First, create a project in Google Cloud.  If you haven't created one before, follow the steps in [this Google tutorial](https://cloud.google.com/appengine/docs/standard/nodejs/building-app/creating-project).

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
* _Note: [Google Cloud Project ID] is the ID of the Google Cloud Project we created earlier, in this case "post-tweet"_

Push the Docker image to your Google Cloud Container registry:
```sh
docker push gcr.io/[Google Cloud Project ID]/post_tweet
```

Then, create a new Cloud Run service:
* In the Google Cloud Console search bar type "cloud run"
* Select "Cloud Run" from the list of options
* In the Cloud Run configuration page, select CREATE SERVICE

![Image of how to create Cloud Run service](https://github.com/sdelgadoc/twitter-bot-as-a-service/blob/master/Images/Create-service-console.png)

In the Create Service configuration page:
* Set the Deployment platform as "Cloud Run (fully managed)"
* For Region, select "us-central1 (Iowa)"
  * This selection is surprisingly important because all the models are in that Region, and if you pick another one, it will degrade performance and increase cost
* For Service name, pick something relevant, in this case I will use "post-a-tweet"
* Finally for Authentication, select "Allow unauthenticated invocations"
  * You will likely want to get more rigorous with authentication, but for now, we're doing this quickly so we can see the result
* Click on NEXT to continue

![Image of how to start configuring a Cloud Run service](https://github.com/sdelgadoc/twitter-bot-as-a-service/blob/master/Images/Create-service.png)

In the Configure the service's first revision page:
* Select Deploy one revision from an existing image
* Click SELECT and search for the Docker container your pushed previously and select it
* Click on Show advanced setting

![Image of how to select an image](https://github.com/sdelgadoc/twitter-bot-as-a-service/blob/master/Images/Configure-service.png)

In the CONTAINER section of Advanced settings:
* Leave default values for everything except the following:
  * Set Memory Allocated to 4 GiB
  * Set Request timeout to 900
  * Set Maximum requests per container to 1

![Image of how to configure advanced container settings](https://github.com/sdelgadoc/twitter-bot-as-a-service/blob/master/Images/Advanced-settings-container.png)

In the VARIABLES section of Advanced settings:
* Click on "+ ADD VARIABLE" to add environmental variables necessary for the script to run
  * We are going to create environmental variables to store your Twitter Application's aunthentication credentials
  * If you don't have a Twitter Application yet, [follow these steps](https://developer.twitter.com/en/docs/apps/overview) to create one
* Create the following four environmental variables with their respective values:
  1. CONSUMER_KEY
  2. ACCESS_TOKEN
  3. ACCESS_TOKEN_SECRET
  4. CONSUMER_SECRET
* Finally create the following environmental variable to generate improved logging in Google Cloud, and set the value to "TRUE"
  1. PYTHONUNBUFFERED

![Image of how to configure advanced variable settings](https://github.com/sdelgadoc/twitter-bot-as-a-service/blob/master/Images/Advanced-settings-variables.png)

You are done!  Click on CREATE to create your Cloud Run service

## Usage
The endpoint that you created will post a tweet when it receives a POST request with JSON data in the format below:
```json
{
    "tweet_type" : "ORIGINAL",
    "usernames" : ["NateSilver538"],
    "model" : "538"
}
```

* Tweet type: A single string that specifies whether you want to post an original tweet to the account's timeline, or reply to another account's tweet.  Values can be "ORIGINAL" or "REPLY"
* Usernames: An array of strings with Twitter account names.  If 'tweet_type' is "ORIGINAL", the model uses the first word of the account's latest tweet as a seed to generate a tweet.  If 'tweet_type' is "REPLY", the model uses the array of accounts to find the most recent tweet to repond to.
* Model: The GPT-2 model that should be used to generate the tweet.  Currently, options are: "538" based on data journalist accounts, "GOP" based on Republican political accounts, "DNC" based on Democratic political accounts

To call your endpoint you can send the POST request with the following command:
```sh
curl -d '{"tweet_type" : "ORIGINAL","usernames" : ["NateSilver538"],"model" : "538"}' -H 'Content-Type: application/json' https://[your-google-run-endpoint]
```

## Maintainer

Santiago Delgado  ([@santiagodc](https://twitter.com/santiagodc))

# Appendix
If you would like to run this Docker image locally, follow these steps:

Just as you did before, make this repo's directory your current directory, and build the Docker image:
Build the Docker immage using the following command (this assumes you have Docker installed):
```sh
docker build -t post_tweet:latest .
```

Then, run the image locally using the following command:
```sh
docker run \
-p 8080:8080 \
-e CONSUMER_KEY='[your Twitter app's value]' \
-e ACCESS_TOKEN='[your Twitter app's value]' \
-e ACCESS_TOKEN_SECRET='[your Twitter app's value]' \
-e CONSUMER_SECRET='[your Twitter app's value]' \
-e PYTHONUNBUFFERED=TRUE \
-e PORT='8080' \
post_tweet:latest
```

Finally, to call your endpoint you can send the POST request with the following command:
```sh
curl -d '{"tweet_type" : "ORIGINAL","usernames" : ["NateSilver538"],"model" : "538"}' -H 'Content-Type: application/json' http://localhost:8080
```

## License

MIT

## Disclaimer

This repo has no affiliation with Twitter Inc.
