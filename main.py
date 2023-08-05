import datetime
import io
import os
import re
import sys
import traceback

import discord
import requests
import requests_cache
import ujson

intents = discord.Intents.none()
intents.message_content = True
client = discord.Client(intents=intents)


def main():
    with open('secret.txt', 'r') as secret_txt:
        secret = secret_txt.read()

    requests_cache.install_cache('dl_cache')
    client.run(secret, log_handler=None)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}\n")
    test_channel_id = 1137437338000162938
    real_channel_id = 617809769322774533
    channel = await client.fetch_channel(test_channel_id)

    if SCRAPING:
        await scrape(channel)
    else:
        await post(channel)

    print("\nDONE")
    await client.close()


async def scrape(channel: discord.TextChannel):
    with open('oldest_scraped.txt', 'r+') as oldest_scraped_file:
        oldest_scraped_read = oldest_scraped_file.read()

        if oldest_scraped_read:
            oldest_scraped = datetime.datetime.fromtimestamp(int(oldest_scraped_read))
            oldest_scraped.replace(tzinfo=datetime.timezone.utc)
        else:
            oldest_scraped = datetime.datetime.now()

        async for message in channel.history(limit=None, oldest_first=True, before=oldest_scraped):
            gfycat_url_result = re_gfycat_url.search(message.content)

            if not gfycat_url_result:
                continue

            message_timestamp = int(message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())
            tags = ' '.join([word for word in message.content.split() if word.startswith('#')])
            message_data = {'author_id': message.author.id, 'author_name': message.author.display_name, 'time': message_timestamp, 'link': message.jump_url,
                            'gfycat_url': gfycat_url_result.group(), 'tags': tags, 'content': message.content}
            print(message_data)

            if not tags:
                print("WARNING: no tags")

            with open(f'messages\\{message.id}.json', 'w', encoding='UTF8') as message_file:
                ujson.dump(message_data, message_file, indent=4, escape_forward_slashes=False)

            oldest_scraped_file.seek(0)
            oldest_scraped_file.truncate()
            oldest_scraped_file.write(str(message_timestamp))


async def post(channel: discord.TextChannel):
    with open('posted.txt', 'r+') as posted_file:
        posted_messages = posted_file.read()

        for message_filename in os.listdir('messages'):
            if message_filename in posted_messages:
                print(f"Skipping {message_filename}")
                continue

            with open(f'messages\\{message_filename}', 'r') as message_file:
                message_data = ujson.load(message_file)

            print(message_data)
            gif_html = requests.get(message_data['gfycat_url'], timeout=10).text
            video_url = re_video_url.search(gif_html).group()
            video_file = discord.File(io.BytesIO(requests.get(video_url, timeout=20).content), filename=video_url.rpartition('/')[2])
            thread_message = (f"Strat by: <@{message_data['author_id']}>"
                              f"\nPosted on: <t:{message_data['time']}:f>"
                              f"\nOriginal message: {message_data['link']}"
                              f"\n\n{message_data['content']}")
            thread = await channel.create_thread(name=f"{message_data['tags']} from {message_data['author_name']}", type=discord.ChannelType.public_thread)
            await thread.send(thread_message, file=video_file, suppress_embeds=True, allowed_mentions=discord.AllowedMentions(users=False))
            await thread.edit(archived=True)

            async for message in channel.history(limit=3):
                if message.author == client.user:
                    await message.delete()
                    break

            posted_file.write(f'{message_filename}\n')


@client.event
async def on_error(*args):
    print(traceback.format_exc(), file=sys.stderr)


SCRAPING = False
re_gfycat_url = re.compile(r'https://gfycat\.com/[A-Za-z]+')
re_video_url = re.compile(r'https://giant\.gfycat\.com/[A-Za-z]+\.mp4')

if __name__ == '__main__':
    main()
