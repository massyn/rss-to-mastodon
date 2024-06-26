# rss-to-mastodon
Publish RSS feeds to Mastodon

## What it is?

This is a simple bot I created to read a number of RSS feeds, and publish the result to a Mastodon [user](https://infosec.exchange/@securityuser).

## How it works

* The script is scheduled via [GitHub Actions](https://docs.github.com/en/actions) and runs every 3 hours.
* It reads the user's [timeline](https://docs.joinmastodon.org/methods/timelines/#home) via an API call, to determine the last time a status update was performed.
* Using the [feedparser](https://pypi.org/project/feedparser/) library, a [list of RSS feeds](config.yaml) are read.
* Any post that is greater than the last time a status update was made, is then posted to Mastodon through an [API call](https://docs.joinmastodon.org/methods/statuses/#create).


## Getting started

The [config.yaml](config.yaml) is split up in different sections, allowing the bot to post multiple feeds to multiple Mastodon channels.

Environment variables `*_ENDPOINT` and `*_ACCESS_KEY` will be used.  Create a set for each section in the config file.

* `{section}_ENDPOINT`
* `{section}_ACCESS_KEY`
