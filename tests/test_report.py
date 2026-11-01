from io import StringIO

from pology.report import init_file_progress


class NonTTYMock:

    def isatty(self):
        return False


class FlushRecorder(StringIO):

    def __init__(self):
        StringIO.__init__(self)
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        StringIO.flush(self)


def test_progress_file():
    paths = ["a.po", "b.po", "c.po"]
    progstream = FlushRecorder()
    update_progress = init_file_progress(
        paths, stream=NonTTYMock(), progstream=progstream
    )
    for path in paths:
        update_progress(path)
        update_progress(path)
    update_progress()
    assert progstream.getvalue().splitlines() == [
        "1/3\ta.po",
        "2/3\tb.po",
        "3/3\tc.po",
    ]
    assert progstream.flushes == len(paths)


def test_progress_file_absent():
    update_progress = init_file_progress(["a.po"], stream=NonTTYMock())
    assert update_progress("a.po") == "a.po"
