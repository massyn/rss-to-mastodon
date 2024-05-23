import yaml
import feedparser
import dateparser
import datetime
import re
import os
from mastodon import Mastodon

def log(txt):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{ts} - {txt}")

def remove_tags(text):
    return re.compile(r'<[^>]+>').sub('', text)

def main(c):
    # Read the configuration
    try:
        with open(c,'rt') as y:
            cfg = yaml.safe_load(y)        
    except:
        log(f"Could not read {c} - ending...")
        exit(1)

    # Loop through each of the sections
    for section in cfg:
        log(f"Section ==> {section}")
        # -- we need our mastodon id, so lets set things up

        if not os.environ.get(f"{section}_ENDPOINT"):
            log(f"ERROR - Environment variable {section}_ENDPOINT is not set.")
            continue
        if not os.environ.get(f"{section}_ACCESS_TOKEN"):
            log(f"ERROR - Environment variable {section}_ACCESS_TOKEN is not set.")
            continue

        mastodon = Mastodon(
            api_base_url = os.environ[f"{section}_ENDPOINT"],
            access_token = os.environ[f"{section}_ACCESS_TOKEN"]
        )
        try:
            me = mastodon.account_verify_credentials()
        except:
            log("ERROR - something is wrong with the credentials.. Skipping...")
            me = {}

        if me.get('id'):
            log(f" - id = {me['display_name']} ({me['id']})")
            
            # -- Find the last time something was posted
            status = mastodon.account_statuses(id=me['id'],limit=1)
            if len(status) == 0:
                log(f" - {section} - Posting - 'Welcome to the RSS Bot'")
                mastodon.status_post('Welcome to the RSS Bot')
            else:
                latest = status[0]['created_at']
                log(f" - {section} - Latest timestamp from timeline is {latest}")

                # -- read through each of the RSS feeds
                for rss in cfg[section]:
                    log(f" - {section} - rss => {rss}")

                    try:
                        # Some sites are blocking us.  Not sure why -- it's RSS!  It's supposed to be scraped...
                        feed = feedparser.parse(rss, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
                    except:
                        feed = {}
                    log(f" - {section} -     => Found {len(feed.get('entries',[]))} items...")

                    # -- check each of the entries, and post if the item was published after our last status was sent.

                    # TODO - add a label or tag to each post to indicate it was automated, so we only
                    # check on the automated posted items. When posting manual messages, that could cause
                    # the bot not to publish anything, since the timestamp has changed.
                    for f in feed.get('entries',[]):
                        published_date = dateparser.parse(f['published'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : True})
                        if published_date > latest:
                            log(f" - {section} -     => Posting - {f['title']}")
                            msg = f'''{feed['feed']['title']} - {f['title']})\n\n{remove_tags(f['summary'])}\n\n{f['link']}'''
                            mastodon.status_post(msg)

    log(" ** All done **")

if __name__=='__main__':
    main('config.yaml')