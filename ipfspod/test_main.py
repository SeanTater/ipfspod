""" Test the main script of ipfspod """
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import check_call, check_output

POD = ["python3", "-m", "ipfspod"]


def test_cli():
    """ Test that ipfspod new, add, and publish work as expected """
    try:
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp.joinpath("foo")
            check_call(POD + ["new", home.as_posix()])

            episodes = home.joinpath("episodes.json")
            assert home.is_dir()
            assert home.joinpath("channel.json").is_file()
            assert home.joinpath("channel.json").stat().st_size > 10
            assert episodes.is_file()
            assert episodes.stat().st_size == 0
            assert home.joinpath("feed_template.xml.jinja").is_file()
            assert (
                home.joinpath("feed_template.xml.jinja").stat().st_size
                > 1000
            )
            assert b"foo" in check_output(["ipfs", "key", "list"])

            check_call(POD + ["add", home.as_posix(), "CIRCLE"])
            assert "CIRCLE" in episodes.read_text()
            check_call(POD + ["add", home.as_posix(), "OVAL", "-d", "DISK"])
            assert "OVAL" in episodes.read_text()
            assert "DISK" in episodes.read_text()
            check_call(POD + [
                "add", home.as_posix(),
                "OVAL",
                "-e", "ELLIPSE", "192", "application/x-helix"
            ])
            assert "ELLIPSE" in episodes.read_text()
            assert "192" in episodes.read_text()
            assert "x-helix" in episodes.read_text()

            check_call(POD + ["add", home.as_posix(), "OVAL", "-a", "SPHERE"])
            assert "SPHERE" in episodes.read_text()

            check_call(POD + ["add", home.as_posix(), "OVAL", "-l", "POINT"])
            assert "POINT" in episodes.read_text()

            check_call(POD + ["publish", home.as_posix(), "-n"])
            feed = home.joinpath("latest_feed.xml").read_text()
            assert "CIRCLE" in feed
            assert "OVAL" in feed
            assert "ELLIPSE" in feed
            assert "SPHERE" in feed
            assert "POINT" in feed
            assert "192" in feed
            assert "x-helix" in feed
    finally:
        check_call(["ipfs", "key", "rm", "foo"])

