# IPFSPod: Video Channels on IPFS
Publish your own content in a channel on IPFS,
using RSS and peer to peer file sharing to get an effect similar to channels
on video streaming websites.

# Install IPFS and IPFSPod
First, you need to install [Interplanetary Filesystem](ipfs.io). It powers the
whole show and without it you have nothing.

```sh
# Make sure ipfs is in your $PATH
which ipfs  # This must work or else you'll get nothing
python3 -m pip install ipfspod  # Now install ipfspod
```

# Create a new channel
If you don't already have a podcast, create one.
The name needs to be pretty short, with no special characters, as it's used in
a lot of contexts. If you want something fancier, you can edit the displayed
parts in a moment.

```sh
python3 -m ipfspod new isnt_nature_neat
cd isnt_nature_neat
```

# Add an episode to your channel
Adding a new episode is pretty painless, but you can make it as detailed as you
want.

> We're assuming you're in the channel directory. If not, then change `.`
> to that directory

```sh
python3 -m ipfspod add . \
    'Found a lizard in the back yard, neat!' \
    -f the_cool_lizard.webm

# Most RSS metadata is supported, like --link, --source, and --author
```

# Publish your channel

Once you have added your episode, or a few if you want, regenerate and publish
your new feed!

```sh
python3 -m ipfspod publish .

# You can also use -n to check the results before actually publishing
```

> Contrary to video sharing sites, adding a video is fast because you don't
> upload it. But publishing your feed can take 1-5 minutes. So when you add a
> post, we don't publish it automatically. That way you can add several posts
> at once and only wait for it to publish once. Conveniently, publishing
> takes about the same amount of time no matter how large the video.