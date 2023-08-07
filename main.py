import datetime
import enum
import io
import os
import re
import sys
import time
import traceback

import discord
import requests
import requests_cache
import ujson

intents = discord.Intents.none()
intents.message_content = True
client = discord.Client(intents=intents)
modes = enum.Enum('Modes', ['scraping', 'downloading', 'posting'])
MODE = modes.posting


def main():
    with open('secret.txt', 'r') as secret_txt:
        secret = secret_txt.read()

    requests_cache.install_cache(r'E:\strats_dl_cache.sqlite')
    client.run(secret, log_handler=None)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}\n")
    test_channel_id = 1137437338000162938
    main_channel_id = 617809769322774533
    mod_channel_id = 923103459354480691
    deathless_channel_id = 946912583716319332
    channel = await client.fetch_channel(deathless_channel_id)
    messages_dir = f'messages_{channel.id}'

    if not os.path.isdir(messages_dir):
        os.mkdir(messages_dir)
        time.sleep(0.2)

    match MODE:
        case modes.scraping:
            await scrape(channel, messages_dir)
        case modes.downloading:
            await download(messages_dir)
        case modes.posting:
            await post(channel, messages_dir)
        case _:
            print("Invalid mode")

    print("\nDONE")
    await client.close()


async def scrape(channel: discord.TextChannel, messages_dir: str):
    oldest_scraped_filename = f'oldest_scraped_{channel.id}.txt'

    if not os.path.isfile(oldest_scraped_filename):
        open(oldest_scraped_filename, 'wb').close()

    with open(oldest_scraped_filename, 'r+') as oldest_scraped_file:
        oldest_scraped_read = oldest_scraped_file.read()

        if oldest_scraped_read:
            oldest_scraped_timestamp = int(oldest_scraped_read)
        else:
            oldest_scraped_timestamp = {617809769322774533: 1567443600, 923103459354480691: 1640973600, 946912583716319332: 1646330400}[channel.id]

        async for message in channel.history(limit=None, oldest_first=True, after=datetime.datetime.fromtimestamp(oldest_scraped_timestamp)):
            gfycat_url_result = re_gfycat_url.findall(message.content)

            if not gfycat_url_result:
                if 'gfycat' in message.content:
                    print(f"WARNING: Schrödinger's gfycat: {message.jump_url}")

                continue

            message_timestamp = int(message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())
            tags = ' '.join([word for word in message.content.split() if word.startswith('#')])
            message_data = {'author_id': message.author.id, 'author_name': message.author.display_name, 'time': message_timestamp, 'link': message.jump_url,
                            'gfycat_urls': gfycat_url_result, 'tags': tags, 'content': message.content}
            print(message_data)

            if not tags:
                print("WARNING: no tags")

            with open(f'{messages_dir}\\{message.id}.json', 'w', encoding='UTF8') as message_file:
                ujson.dump(message_data, message_file, indent=4, escape_forward_slashes=False, ensure_ascii=False)

            oldest_scraped_file.seek(0)
            oldest_scraped_file.truncate()
            oldest_scraped_file.write(str(message_timestamp))
            oldest_scraped_file.flush()


async def download(messages_dir: str):
    for message_filename in os.listdir(messages_dir):
        with open(f'{messages_dir}\\{message_filename}', 'r') as message_file:
            message_data = ujson.load(message_file)

        print(message_data)

        for url in message_data['gfycat_urls']:
            video_data, video_filename = download_from_gfycat_url(url)
            print(len(video_data), video_filename)


async def post(channel: discord.TextChannel, messages_dir: str):
    posted_filename = f'posted_{channel.id}.txt'

    if not os.path.isfile(posted_filename):
        open(posted_filename, 'wb').close()

    with open(posted_filename, 'r+') as posted_file:
        posted_messages = posted_file.read()

        for message_filename in os.listdir(messages_dir):
            if message_filename in posted_messages:
                print(f"Skipping {message_filename}")
                continue

            with open(f'{messages_dir}\\{message_filename}', 'r', encoding='UTF8') as message_file:
                message_data = ujson.load(message_file)

            print(message_data)

            thread = await channel.create_thread(name=f"{message_data['tags'][:70]} from {message_data['author_name']}", type=discord.ChannelType.public_thread)
            video_files = []

            for url in message_data['gfycat_urls']:
                video_data, video_filename = download_from_gfycat_url(url)
                video_files.append(discord.File(io.BytesIO(video_data), filename=video_filename))

            thread_message = (f"Strat by: <@{message_data['author_id']}>"
                              f"\nPosted on: <t:{message_data['time']}:f>"
                              f"\nOriginal message: {message_data['link']}"
                              f"\n\n{message_data['content']}")
            await thread.send(thread_message, files=video_files, suppress_embeds=True, allowed_mentions=discord.AllowedMentions(users=False))
            await thread.edit(archived=True)

            async for message in channel.history(limit=1):
                if message.author == client.user:
                    await message.delete()

            posted_file.write(f'{message_filename}\n')
            posted_file.flush()


def download_from_gfycat_url(url: str) -> tuple[bytes, str]:
    gif_html = requests.get(url, timeout=10).text
    video_url = re_video_url.search(gif_html).group()
    return requests.get(video_url, timeout=20).content, video_url.rpartition('/')[2]


@client.event
async def on_error(*args):
    print(traceback.format_exc(), file=sys.stderr)


re_gfycat_url = re.compile(r'https://gfycat\.com/[A-Za-z]+')
re_video_url = re.compile(r'https://giant\.gfycat\.com/[A-Za-z]+\.mp4')
# oldest scrapes
# main: 1567443600
# mods: 1640973600
# deathless: 1646330400

if __name__ == '__main__':
    main()
