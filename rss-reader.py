import yaml
import feedparser
import dateparser
import datetime
import re
import os
import logging
from mastodon import Mastodon
import socket
from dotenv import load_dotenv

load_dotenv()
socket.setdefaulttimeout(10)          # seconds  ← change once, applies everywhere
logging.basicConfig(
    level="DEBUG",
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

def read_rss(feed):
    logging.info(f"Reading RSS feed {feed}")
    try:
        # Some sites are blocking us.  Not sure why -- it's RSS!  It's supposed to be scraped...
        feed = feedparser.parse(feed, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
        logging.info(f" --> Found {len(feed.get('entries',[]))} items...")
        return feed
    except socket.timeout:
        logging.warning(" --> timed out after 10s")
    except Exception as exc:
        logging.error(" --> failed: %s", exc)
    return None

def filter_rss(feed,latest):
    data = []
    if feed != None:
        for f in feed.get('entries',[]):
            if 'published' in f and 'summary' in f:
                published_date = dateparser.parse(f['published'],settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE' : True})
                if published_date > latest:
                    data.append({
                        'feed_title'        : feed.get('feed',{}).get('title','No title'),
                        'published_date'    : published_date,
                        'title'             : f['title'],
                        'summary'           : re.compile(r'<[^>]+>').sub('', f['summary']),
                        'link'              : f['link']
                    })
    return data

def test(c):
    # Read the configuration
    try:
        with open(c,'rt') as y:
            cfg = yaml.safe_load(y)        
    except:
        logging.error(f"Could not read {c} - ending...")
        exit(1)

    # Loop through each of the sections
    for section in cfg:
        logging.info(f"Section ==> {section}")
        # -- read through each of the RSS feeds
        content = []
        for rss in cfg[section]:
            logging.info(f" - {section} - rss => {rss}")

            feed = read_rss(rss)
            content += filter_rss(feed, datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3))

        if len(content) < 5:
            for i in content:
                logging.info(f" - {section} -     => Posting - {i['feed_title']}")
                msg = f'''{i['feed_title']} - {i['title']}\n\n{i['summary']}\n\n{i['link']}'''
                print(msg)
        else:
            logging.info(f" - {section} -     => Posting Digest")
            msg = "Digest of security news:\n\n"

            for i in content:
                msg += f'''* <a href="{i['link']}">{i['feed_title']} - {i['title']}</a>\n'''
            print(msg)

def main(c):
    # Read the configuration
    try:
        with open(c,'rt') as y:
            cfg = yaml.safe_load(y)        
    except:
        logging.error(f"Could not read {c} - ending...")
        exit(1)

    # Loop through each of the sections
    for section in cfg:
        logging.info(f"Section ==> {section}")

        # -- we need our mastodon id, so lets set things up
        if not os.environ.get(f"{section}_ENDPOINT"):
            logging.error(f"Environment variable {section}_ENDPOINT is not set.")
            continue
        if not os.environ.get(f"{section}_ACCESS_TOKEN"):
            logging.error(f"Environment variable {section}_ACCESS_TOKEN is not set.")
            continue

        mastodon = Mastodon(
            api_base_url = os.environ[f"{section}_ENDPOINT"],
            access_token = os.environ[f"{section}_ACCESS_TOKEN"]
        )
        try:
            me = mastodon.account_verify_credentials()
        except:
            logging.error("Something is wrong with the credentials.. Skipping...")
            me = {}

        if me.get('id'):
            logging.info(f" - id = {me.get('display_name')} ({me.get('id')})")
            
            # -- Find the last time something was posted
            status = mastodon.account_statuses(id=me.get('id'),limit=1)
            if len(status) == 0:
                logging.info(f" - {section} - Posting - 'Welcome to the RSS Bot'")
                mastodon.status_post('Welcome to the RSS Bot')
            else:
                latest = status[0]['created_at']
                logging.info(f" - {section} - Latest timestamp from timeline is {latest}")

                # -- read through each of the RSS feeds
                content = []
                for rss in cfg[section]:
                    logging.info(f" - {section} - rss => {rss}")

                    feed = read_rss(rss)
                    content += filter_rss(feed,latest)
                if len(content) < 5:
                    for i in content:
                        logging.info(f" - {section} -     => Posting - {i['feed_title']}")
                        msg = f'''{i['feed_title']} - {i['title']}\n\n{i['summary']}\n\n{i['link']}'''
                        mastodon.status_post(msg[:10000])
                else:
                    logging.info(f" - {section} -     => Posting Digest")
                    msg = "Digest of security news:\n\n"

                    for i in content:
                        msg += f'''* <a href="{i['link']}">{i['feed_title']} - {i['title']}</a>\n'''
                    mastodon.status_post(msg[:10000])

    logging.info(" ** All done **")

if __name__=='__main__':
    main('config.yaml')
    #test('config.yaml')