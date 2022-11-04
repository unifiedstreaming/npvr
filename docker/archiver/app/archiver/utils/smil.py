from collections.abc import MutableSequence
from datetime import datetime
from isodate import parse_datetime
from lxml import etree


NSMAP = {None: "http://www.w3.org/2001/SMIL20/Language"}


class SMIL(MutableSequence):
    """
    SMIL object
    reimplementation in a hopefully more sensible and extensible way
    """

    def __init__(self, playlist=None):
        self._list = list()
        if playlist is not None:
            self._list.extend(playlist)

    def __len__(self):
        return len(self.list)

    def __getitem__(self, index):
        return self.list[index]

    def __setitem__(self, index, value):
        self.check(value)
        self.list[index] = value

    def __delitem__(self, index):
        del self.list[index]

    def insert(self, index, value):
        self.check(value)
        self.list.insert(index, value)

    def check(self, value):
        if not isinstance(value, SMILItem):
            raise TypeError(f"{value} is not a SMILItem")

    def __str__(self):
        return str(
            etree.tostring(
                self.element(),
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
            ),
            "UTF-8",
        )

    @property
    def list(self):
        return self._list

    @list.setter
    def list(self, l):
        if not isinstance(l, list):
            raise TypeError("must be a list")
        elif all([self.check(x) for x in l]):
            self._list = l

    def element(self):
        el = etree.Element("smil", nsmap=NSMAP)
        head = etree.Element("head")
        el.append(head)
        body = etree.Element("body")
        seq = etree.Element("seq")
        for i in self.list:
            seq.append(i.element())
        body.append(seq)
        el.append(body)

        return el


class SMILItem(object):
    """
    Line item within SMIL
    """

    def __init__(self, src, begin=None, end=None):
        self._src = src
        self._begin = begin
        self._end = end

    # properties
    @property
    def src(self):
        return self._src

    @src.setter
    def src(self, src):
        if isinstance(src, str):
            self._src = src
        else:
            raise TypeError("src must be a string")

    @property
    def begin(self):
        return self._begin

    @begin.setter
    def begin(self, begin):
        if isinstance(begin, datetime):
            self._begin = begin
        else:
            try:
                self._begin = parse_datetime(begin)
            except Exception:
                raise TypeError("begin should be a datetime")

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        if isinstance(end, datetime):
            self._end = end
        else:
            try:
                self._end = parse_datetime(end)
            except Exception:
                raise TypeError("end should be a datetime")

    def element(self):
        """Return SMIL XML element"""
        el = etree.Element("video", nsmap=NSMAP)
        el.set("src", self.src)
        if self.begin is not None:
            el.set(
                "clipBegin",
                f"wallclock({self.begin.isoformat().replace('+00:00', 'Z')})",
            )
        if self.end is not None:
            el.set(
                "clipEnd",
                f"wallclock({self.end.isoformat().replace('+00:00', 'Z')})",
            )
        return el

    def __str__(self):
        return str(
            etree.tostring(
                self.element(),
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
            ),
            "UTF-8",
        )
