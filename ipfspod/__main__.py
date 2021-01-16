""" Manage IPFS podcasts via a simple command line script. """
from argparse import ArgumentParser
import json
from pprint import pprint
import subprocess
from pathlib import Path
from datetime import datetime
import random
import base64

from jinja2 import Environment, FileSystemLoader, select_autoescape
import filetype
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

import ipfspod

parser = ArgumentParser(
    description="Publish podcasts on IPFS"
)
subparsers = parser.add_subparsers(help="Command")
parser.set_defaults(command=lambda _: parser.print_help())

#
# ipfspod new: Create a new podcast
#
cmd_new = subparsers.add_parser(
    "new",
    description="Create a new podcast, in a new folder",
    epilog="These fields all fill out a template and are easily changed later,"
           " in particular description should probably be longer than is"
           " conveniently given as an option.")
cmd_new.add_argument(
    "channel_name",
    help="Short channel name with no special characters")
cmd_new.add_argument("--title", help="Longer, human readable channel title")
cmd_new.add_argument(
    "--description",
    help="Detailed channel description, optionally in HTML.")
cmd_new.add_argument("--link", help="Link to the podcast home page")
cmd_new.add_argument(
    "--copyright",
    help="Copyright information (peer-to-peer; not every license makes sense)")
cmd_new.add_argument(
    "--language", default="en",
    help="Language as a two character code,"
         " plus optional variant (e.g. 'en', 'en-US')")
cmd_new.add_argument(
    "--managing-editor", "--author", default="anonymous",
    help="Channel's managing editor: in most cases also the sole author")
cmd_new.add_argument(
    "--ttl", type=int, default=1800,
    help="Recommended time between client refreshes, in seconds")
cmd_new.add_argument(
    "--key",
    help="Don't create a key for this channel: use this key instead")


def run_new(args):
    """ Create a new podcast

        This creates a new directory and fills it with a few standard
        templates, creating a new IPNS key

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
    """
    channel_name = Path(args.channel_name).name
    title = args.title or channel_name.replace("_", " ").title()
    home = Path(args.channel_name).absolute()
    home.mkdir()

    key = args.key or (
        subprocess
        .check_output(["ipfs", "key", "gen", home.name])
        .decode()
        .strip()
    )
    metadata = dict(
        title=title,
        description=args.description or title,
        link=args.link or "http://localhost:8080/ipns/"+key,
        copyright=args.copyright or "CC-BY 4.0 Intl.",
        language=args.language or "en",
        managing_editor=args.managing_editor or "anonymous",
        ttl=args.ttl,
        key=key
    )

    print(
        f"Generating a new channel {title} in {home.as_posix()}"
        " with the following properties:"
    )
    pprint(metadata)

    home.joinpath("channel.json").write_text(json.dumps(metadata))
    home.joinpath("feed_template.xml.jinja").write_text(
        pkg_resources.read_text(ipfspod, "feed_template.xml.jinja")
    )
    home.joinpath("episodes.json").touch()


cmd_new.set_defaults(command=run_new)

#
# ipfspod add: Add a new episode to the channel
#

cmd_add = subparsers.add_parser(
    "add",
    description="Add a new episode to a channel's episode list",
    epilog="The channel must be initialized by `ipfspod new`"
)
cmd_add.add_argument("channel", help="Directory for the channel to append to")
cmd_add.add_argument("title", help="Longer, human readable episode title")
cmd_add.add_argument(
    "-d", "--description",
    help="Detailed episode description, optionally in HTML")
cmd_add.add_argument(
    "-l", "--link", help="Link to a copy of this post, if applicable")
cmd_add.add_argument(
    "-a", "--author", help="Author, if different from managing editor")
cmd_add.add_argument(
    "-c", "--category", nargs="+", default=[],
    help="Category or tag for this post. Conventially nested with '/',"
    " like 'tech/linux/admin'. You can also specify multiple,"
    " e.g. '-c health/fitness health/weight-loss'")
cmd_add.add_argument(
    "-f", "--file", action="append", default=[],
    help="Attach a file to this post. Requires ipfs installed in $PATH")
cmd_add.add_argument(
    "-e", "--enclosure", action="append", nargs=3, default=[],
    metavar=("HASH", "LENGTH_IN_BYTES", "MIMETYPE"),
    help="Attach a file specifying details directly instead of calling ipfs."
         " Use -e multiple times may not be supported by all aggregators.")
cmd_add.add_argument(
    "-s", "--source", help="Link to the feed this was forwarded from, if any")


def run_add(args):
    """ Add a new episode to a channel's episode list

        Requires the channel was initialized by `ipfspod new`

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
    """
    home = Path(args.channel).absolute()
    channel = json.loads(home.joinpath("channel.json").read_text())

    # Add any videos or audio to IPFS before writing episode metadata
    new_enclosures = []
    for filename in args.file:
        file_hash = (
            subprocess
            .check_output(["ipfs", "add", "-Q", filename])
            .decode()
            .strip()
        )
        file_len = Path(filename).stat().st_size
        file_type = filetype.guess_mime(filename)
        new_enclosures.append((file_hash, file_len, file_type))

    # Build the episode metadata JSON object
    episode = dict(
        title=args.title,
        description=args.description or args.title,
        link=args.link,
        author=args.author or channel['managing_editor'],
        categories=args.category,
        date=datetime.utcnow().strftime(r"%a, %d %b %Y %H:%M:%SZ"),
        enclosures=[
            # Name the fields and include any we just indexed
            dict(hash=enc[0], len=enc[1], type=enc[2])
            for enc in args.enclosure + new_enclosures
        ],
        # Generates a hash like RLZtAITwyHgorjZ0HYPvl9oYsFFRhIrFhjmZAbbd410=
        # but b64encode creates a bytes() so decode() means convert to str()
        hash=base64.b64encode(
            random.getrandbits(256).to_bytes(32, 'big')
        ).decode(),
        source=args.source
    )

    # Append this to the episode list
    with home.joinpath("episodes.json").open("a") as episodes_file:
        episodes_file.write(json.dumps(episode) + "\n")


cmd_add.set_defaults(command=run_add)

#
# ipfspod gen: Generate a new latest_feed.xml
#

cmd_publish = subparsers.add_parser(
    "publish",
    description="Regenerate the RSS feed and update IPNS",
    epilog="Requires the channel was initialized by `ipfspod new`"
)
cmd_publish.add_argument(
    "channel", help="Channel directory (containing metadata.json)")
cmd_publish.add_argument(
    "-n", "--dry-run", action="store_true",
    help="Generate RSS but don't publish it.")


def run_publish(args):
    """ Generate an RSS feed for a podcast

        Requires the channel was initialized by `ipfspod new`

        Accepts
        -------
        args: a Namespace resulting from ArgumentParser.parse_args
        """
    home = Path(args.channel).absolute()
    channel = json.loads(home.joinpath("channel.json").read_text())
    now = datetime.utcnow().strftime(r"%a, %d %b %Y %H:%M:%SZ")
    episodes = [
        json.loads(line)
        for line in home.joinpath("episodes.json").read_text().splitlines()
    ]
    env = Environment(
        loader=FileSystemLoader(home.as_posix()),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template("feed_template.xml.jinja")
    feed = template.render(channel=channel, episodes=episodes, now=now)
    feed_path = home.joinpath("latest_feed.xml")
    feed_path.write_text(feed)

    if not args.dry_run:
        file_hash = (
            subprocess
            .check_output(["ipfs", "add", "-Q", feed_path.as_posix()])
            .decode()
            .strip()
        )
        subprocess.check_call(
            ["ipfs", "name", "publish", "--key", home.name, file_hash]
        )


cmd_publish.set_defaults(command=run_publish)

# Finally, use the new parser
all_args = parser.parse_args()
# Invoke whichever command is appropriate for the arguments
all_args.command(all_args)
