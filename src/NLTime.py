import re, calendar, datetime, weakref
from PartialTime import PartialTime, partialtime_attrs
from AIMA import *

# TODO distinguish between the main parser and token parsers
# TODO make range objects (which are just 2 times/dates/datetimes)
# datetime + datetime
# date + date
# time + time
# datetime + date (time from first or open ended)
# datetime + time (if time2 is after time1, could be a day/month after)
#   i.e. (5/27 9pm) - 1am
#           dt         t

"""
Some notes for now:
Based on drewp's design which parsed words into these categories:

             n - number
             y - year
             m - month (including abbreviations)
             d - day-of-week
             t - time-of-day (some parsable time, including ambiguous
                 ones like '7:30')
             u - unknown (the default) (these are skipped)

We also have:

             M - AM/PM
             z - timezone
             r - relative marker ("next", "last", "this" -- needs a context)
             - - range marker ("-", "to", "until")

And should add:

             U - time unit ('week', 'hour', 'month' -- combine with relative
                 and context)
"""

# some scoring information
piecetype_scores = {
    'dayofweek' : 5,
    'date' : 5,
    'time' : 5,
    'month' : 4,
    'day' : 3,
    'year' : 2,
    'ampm' : 5,

    # we'd like to have these rather than not, but they're generally less
    # informative
    'relative' : 2,
    'int' : 0,
    'locpiece' : 1,
    'lochint' : 1,
    'timehint' : 1,
    'rangehint' : 1,

    # other parsers
    'dateutil_parseable' : 0,
    'mx_parseable' : 0,
}
common_orders = [
    "dayofweek month day year",
    "dayofweek month day",
    "dayofweek day month year",
    "dayofweek day",
    "month year time",
    "month year hour",
    "month year hour minute",
    "month year hour minute ampm",
    "month day",
    "month day year",
    "month year",
    "month",
    "year",
    "time",
    "time ampm",
    'hour minute ampm',
    'hour minute second ampm',
    'hour minute',
    'hour minute second',
]
common_orders = [tuple(order.split()) for order in common_orders]

days_of_week = [day.lower() for day in calendar.day_name]
month_names = [month.lower() for month in calendar.month_name]

nonint_start = re.compile(r'^[^\d]+')
nonint_end = re.compile(r'[^\d]+$')

punc = r'[\.\,;:\'"\(\)\*\+]'
punc_re = re.compile(r'%s+' % punc)
punc_start_re = re.compile(r'^%s+' % punc)
punc_end_re = re.compile(r'%s+$' % punc)

ws_split = re.compile(r'\s')

ordinals_re = re.compile(r'st|nd|rd|th', re.I)
time_re = re.compile(r'^(\d{1,2})(?:\:?(\d+))?(?:\:?(\d+))?\s*([AP]\.?M\.?)?$', re.I)

# Some date examples:
# 5/27, 6.01.2004, 6.1.2004, 1-2-1981, 1-2-03
date_re = re.compile(r'(\d{1,4})[\./\-](\d{1,4})(?:[\./\-](\d{1,4}))?')

def closest(center, points):
    """Return points sorted by distance from the center."""
    return sorted(points, key=lambda point: abs(center - point))

def is_dayofweek(text):
    text = text.lower()
    text = punc_re.sub('', text)
    # prefix that's at least 3 chars
    if len(text) < 3:
        return None
    for day in days_of_week:
        if (day.find(text) == 0) or (len(day) < len(text) and day in text):
            return days_of_week.index(day) + 1

def is_month(text):
    text = text.lower()
    text = punc_re.sub('', text)
    for month in month_names:
        if text in month and len(text) >= 3: # prefix that's at least 3 chars
            return month_names.index(month)
    else:
        i = is_int(text)
        if i is not None and 1 <= i <= 12:
            return i
        return None

def is_date(text):
    if ordinals_re.search(text):
        return None

    # remove trailing non-numbers
    text = nonint_end.sub('', text)
    text = nonint_start.sub('', text)
    match = date_re.match(text)
    if match:
        results = []
        a, b, c = match.groups()
        # month-day-year and year-month-day
        for month, day, year in ((a, b, c), (b, c, a), (a, c, b)):
            if month:
                m = is_month(month)
            else:
                m = None

            if day:
                d = is_day(day)
            else:
                d = None

            if year is not None:
                y = is_year(year)

            if m and d:
                if year and y: # valid year portion
                    if type(y) is not list:
                        y = [y]
                    results.extend([datetime.date(year, m, d) for year in y])
                elif year: # invalid year portion
                    pass # the date is no good
                else: # missing year portion
                    results.append(PartialTime(month=m, day=d))

            if m and year:
                if type(y) is not list:
                    y = [y]
                results.extend([PartialTime(year=year, month=m) for year in y])

        return results or None

def is_int(text):
    # remove some (but not all) non-numbers
    text = punc_start_re.sub('', text)
    text = punc_end_re.sub('', text)
    text = ordinals_re.sub('', text)
    try:
        return int(text)
    except ValueError:
        return None

def is_hour(text):
    i = is_int(text)
    if i is not None and not ordinals_re.search(text):
        if 1 <= i <= 11:
            return closest(12, (i, i + 12))
        elif 0 <= i <= 23:
            return i
    return None

def is_day(text):
    i = is_int(text)
    if i is not None and 1 <= i <= 31:
        return i
    return None

def is_year(text):
    text = punc_start_re.sub('', text)
    text = punc_end_re.sub('', text)
    if len(text) in (2, 4) and not ordinals_re.search(text):
        i = is_int(text)
        current_year = PartialTime.now().year
        # we'll arbitrarily decide that we're not referring to years
        # more than 200 years in the future
        if i is not None and i < current_year + 200:
            if len(text) == 2:
                return closest(2000, (2000 + i, 1900 + i))
            else:
                return i
        return None

def is_time(text):
    """Returns a list of possible times"""
    text = punc_start_re.sub('', text)
    text = punc_end_re.sub('', text)

    if ordinals_re.search(text):
        return None

    match = time_re.match(text)
    # 3pm (len 3) to 12:45:78pm (len 10)
    if 2 < len(text) < 11 and match and '/' not in text and '-' not in text:
        hour, minute, second, ampm = match.groups()
        # print "match", match.groups()

        # the regex might put the wrong number of digits in the minute part
        # (we'd make the minute parser greedier, but can't get it to work)
        if minute and len(minute) == 1 and len(hour) == 2:
            hour, minute = hour[0], hour[1] + minute

        startswith0 = hour.startswith('0') and len(hour) == 2

        if not minute:
            minute = 0
        else:
            minute = int(minute)

        if not second:
            second = 0
        else:
            second = int(second)

        if ampm:
            ampm = is_ampm(ampm)

        hour = int(hour)

        # now we make sure it's valid
        if (ampm and (hour < 1 or hour > 12)) or \
           (hour < 0 or hour > 23):
            return None
        if (minute < 0 or minute > 59):
            return None
        if (second < 0 or second > 59):
            return None

        if hour > 12:
            # definitely 24h in the PM
            return datetime.time(hour, minute, second)
        elif startswith0 and hour < 12:
            # 24h and in the AM
            return datetime.time(hour, minute, second)
        elif ampm:
            if ampm.upper() == 'PM':
                hour += 12
                hour %= 24
            return datetime.time(hour, minute, second)
        else:
            # we want to pick the time that's closer to noon
            # datetime.datetimes can be compared, datetime.times cannot,
            # so we'll make some datetimes on the same day
            t1, t2 = (datetime.datetime(1, 1, 1, hour, minute, second),
                      datetime.datetime(1, 1, 1, (hour + 12) % 24, minute,
                                        second))
            noon = datetime.datetime(1, 1, 1, 12)

            t1, t2 = closest(noon, (t1, t2))
            return t1.time(), t2.time()
    else:
        text = text.lower().strip()
        text = punc_re.sub('', text)
        if text == 'noon':
            return datetime.time(12)
        elif text == 'midnight':
            return datetime.time(0)

        return None

def is_ampm(text):
    text = text.upper()
    text = punc_re.sub('', text)
    if text in ['AM', 'PM']:
        return text

def is_timehint(text):
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['at', 'from', 'night', 'day', 'is', 'of']:
        return text

def is_rangehint(text):
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['-', 'to', 'until', 'through']:
        return text

# Coming soon!
def is_range(text):
    text = text.strip()
    if text.count('-') == 1:
        left, right = text.split('-')
        if not (left or right):
            return None
        # XXX we should be passing context
        lparse = Parse(left)
        rparse = Parse(right)

        # since the string doesn't have any spaces, (that's what we split on
        # to get the text variable here) lparse and rparse better have exactly
        # one Segment
        if (len(lparse.segments) != 1) or (len(rparse.segments) != 1):
            return None
        lnode = lparse.segments[0][0]
        rnode = rparse.segments[0][0]
        results = []
        for ltype, lparse in lnode.parses:
            for rtype, rparse in rnode.parses:
                if ltype == rtype:
                    # TODO date and time should be in this list when 
                    # PartialTime is fixed
                    if ltype in ('month', 'day', 'year'):
                        if rparse <= lparse:
                            continue
                    results.append((ltype, lparse, rparse))
        # print 'results', results
        return results # these will need to be in a different format

def is_locpiece(text):
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['room', 'rooms', 'building', 'buildings', 'street', 'st',
                'avenue', 'ave', 'floor', 'floors']:
        return text

def is_lochint(text):
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['in', 'on']:
        return text

def is_relative(text):
    """Returns a normalized relative marker if text contains one.  Relative
    markers require a context (and possibly more information) to evaluate."""
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['next', 'last', 'this', 'upcoming', 'previous', 'following',
                'today', 'tonight', 'tomorrow', 'yesterday', 'morning',
                'afternoon', 'evening', 'night', 'now']:
        # normalize some of these
        text = text.replace('following', 'next')
        text = text.replace('upcoming', 'this')
        text = text.replace('previous', 'last')

        return text

ordinals = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh',
            'eigth', 'ninth', 'tenth']

def is_ordinal(text):
    """Attempts to return a normalized ordinal number or None if the
    text is not an ordinal.
    "first" -> 1, "second" -> 2, etc."""
    # TODO list/compute more ordinals? ("twenty-third", etc.)
    text = text.lower()
    text = punc_re.sub('', text)
    try:
        return ordinals.index(text) + 1
    except ValueError:
        without_suffix = ordinals_re.sub('', text)
        if ordinals_re.search(text):
            # this will return None if it's not a number, which is what we want
            i = is_int(without_suffix)
            return i
        return None

# a list of all token parsers
all_parsers = [locals()[name] for name in dir() if name.startswith('is_')]

class ParsedWord:
    def __init__(self, word, linenum, colnum, wordnum, charnum, parsers=None):
        self.originalword = word
        self.linenum = linenum
        self.colnum = colnum
        self.wordnum = wordnum
        self.charnum = charnum
        self.parsers = parsers or all_parsers

        self.parses = []

        for parser in self.parsers:
            # print "word", repr(word), "parser", parser
            results = parser(word)
            if results is not None:
                # print "results", results
                if not isinstance(results, (list, tuple)):
                    results = [results]
                for result in results:
                    # print 'result', result
                    name = parser.__name__.replace('is_', '')
                    self.parses.append((name, result))
    def is_only_hint(self):
        """If this ParsedWord only has parses that are hints"""
        for toktype, parse in self.parses:
            if 'hint' not in toktype:
                return False
        else:
            return True
    def is_only_relative(self):
        """If this ParsedWord only has parses that relative"""
        for toktype, parse in self.parses:
            if 'relative' not in toktype:
                return False
        else:
            return True
    def __str__(self):
        return self.originalword
    def __repr__(self):
        return "<Node %r %d:%d %s>" % (self.originalword, self.linenum,
                                       self.wordnum, str(self.parses))

class Segment(list):
    """A consecutive sequence of ParsedWord objects.  It is a subclass of
    a list, so all list methods will work.  parseobj is a the Parse object
    that contains this Segment.  Context and other scoring information
    will be retrieved from the parseobj."""
    def __init__(self, l=None, parseobj=None):
        list.__init__(self, l or [])
        # we run into problems if a Segment outlives the Parse that it lives
        # in, but I'm not sure how to deal with that situation yet.
        self.parseobj = weakref.proxy(parseobj)
    def __str__(self):
        """Returns a string of all words in this Segment."""
        return ' '.join([parsedword.originalword for parsedword in self])
    def extent(self, charindices=False):
        """Returns the start and end line:column for this segment."""
        first, last = self[0], self[-1]
        if charindices:
            return (first.charnum, last.charnum + len(str(last)))
        else:
            return ((first.linenum + 1, first.colnum),
                    (last.linenum + 1, last.colnum + len(str(last))))
    def just_hints(self):
        """Returns whether this Segment is only hints and relative
        markers."""
        for word in self:
            if not (word.is_only_relative() or word.is_only_hint()):
                return False
        else:
            return True
    def get_parses_by_parser(self, parser):
        results = []
        for word in self:
            for wordparser, val in word.parses:
                if parser == wordparser:
                    results.append(val)
        return results

    def all_compatible(self, seq):
        """Returns whether a segment is potentially valid."""
        head = seq[0]
        tails = seq[1:]
        # head is compatible with every tail
        return every(lambda tail: pieces_compatible(head, tail), tails)

    def valid_parses(self, filter_incomplete=True):
        """Returns all valid parses and their score, ordered by score.
        ((parse1, score1), (parse2, score2), ...)"""
        context = self.parseobj.context or PartialTime.now()

        interpretable_parses = []
        all_parses = cartesianproduct([node.parses for node in self],
                                      self.all_compatible)
        for interp in all_parses:
            # print "interp", interp
            interp = SegmentInterpretation(interp)
            interp.segment = self
            score, result = interp.score(context)
            # print "score", score
            # print "result", repr(result)
            if score > 0 and result:
                if filter_incomplete and not result.is_interpretable():
                    continue
                interpretable_parses.append((score, result))
        
        scores = {} # interp : best score
        for score, interp in interpretable_parses:
            if (interp in scores and score > scores[interp]) or \
               (interp not in scores):
                scores[interp] = score

        parses = sortedtimes(scores.items(), context)
        return parses

# let's do the Time Sort again!
def sortedtimes(times_and_scores, context=None):
    """Sort times by score then by distance to the context.
    times_and_scores is a list of tuples of (PartialTime object, score).
    context is a PartialTime or None (for "now").  Returns a list in the
    same format as times_and_scores (but a potentially different order)"""
    # sort by scores then by distance to the context
    def sortkey((parse, score)):
        try:
            delta = parse - context
            days, secs = -abs(delta.days), -abs(delta.seconds)
        except TypeError: # things that are incomparable raise a TypeError
            days, secs = None, None # None is less than all numbers
        return (score, days, secs)
    
    sorted_times_and_scores = sorted(times_and_scores, key=sortkey,
        reverse=True)

    return sorted_times_and_scores

class SegmentInterpretation(tuple):
    def __init__(self, *args):
        tuple.__init__(self, *args)
        self.parsedict = dict(self)
        self.segment = None
    def grammar_score(self):
        ourorder = tuple([parser for parser, val in self])
        # we might want to make some grammars worth more than others at some
        # point
        if ourorder in common_orders:
            return 5
        else:
            return 0
    def score(self, context):
        """Return the score of this SegmentInterpretation given a context."""
        result = self.convert_parse_to_date_and_time(context)
        if not result:
            return (0, result)
        score = self.grammar_score()
        # print "score", self.parsedict, repr(result)
        if 'dayofweek' in self.parsedict and 'month' in self.parsedict:
            try:
                # they're 0-based, we're 1-based
                year, month, day = result.year, result.month, result.day
                dayofweek = self.parsedict['dayofweek']
                realdayofweek = result.weekday() + 1
                if realdayofweek == dayofweek:
                    score += 10
            except AttributeError:
                pass

        # extra points for having these objects complete
        d = result.as_date()
        t = result.as_time()
        if d and t:
            score += 11
        elif d or t:
            score += 5

        for (piecetype, val) in self:
            score += piecetype_scores.get(piecetype, 0)

        # print "score", score, result
        return score, result

    def convert_parse_to_date_and_time(self, context):
        """In this method, we attempt to convert this SegmentInterpretation
        into a PartialTime.  We use context to try to fill in missing
        information.  Relative markers are expanded here."""
        # we run through all items and expand all date, datetimes, and times
        # (or anything with the right attributes)
        for tokenparser, result in self:
            # datetime.datetime is a child of datetime.date, so this covers
            # all three of them
            for attr in partialtime_attrs:
                try:
                    if attr not in self.parsedict:
                        expansion = getattr(result, attr)
                        if expansion is not None:
                            self.parsedict[attr] = expansion
                except AttributeError:
                    pass

        # fill in the current year if we don't have it but have part of a date
        if self.parsedict.get('month') is not None:
            if self.parsedict.get('year') is None:
                self.parsedict['year'] = context.year
        # fill in 0 for the minute if we have part of a time
        if 'hour' in self.parsedict:
            if not 'minute' in self.parsedict:
                self.parsedict['minute'] = 0

        for expfunc in (self.expand_day_relatives,
                        self.expand_dayofweek_with_relatives,
                        self.expand_ordinal_dow_month):
            expansion = expfunc(context)
            if expansion is not None:
                return expansion
        else:
            pt = PartialTime.from_object(self.parsedict)
            return pt

    def expand_day_relatives(self, context):
        """Expands 'yesterday', 'today', 'tonight', 'tomorrow', and 'now'."""
        if 'relative' in self.parsedict:
            rel = self.parsedict['relative']
            try:
                if rel == 'now':
                    return context

                if rel == 'tonight':
                    rel = 'today'
                day_offset = ['yesterday', 'today', 'tomorrow'].index(rel) - 1
                day_delta = datetime.timedelta(days=day_offset)
                original = PartialTime.from_object(self.parsedict)
                newdate = PartialTime.from_object(context.as_date() + day_delta)
                return original.combine(newdate)
            except ValueError:
                pass

        return None

    def expand_dayofweek_with_relatives(self, context):
        """Perform a day of week expansion given a relative ("this monday", 
        "next tuesday", etc.)"""
        without_dow = self.parsedict.copy()
        dow = without_dow.pop('dayofweek', None)
        # if we have a dayofweek but no date elements
        if dow and not (without_dow.get('year') or \
                        without_dow.get('month') or \
                        without_dow.get('day')):
            rel = self.parsedict.get('relative', 'this')

            try:
                offset = ['last', 'this', 'next'].index(rel) - 1
                p = PartialTime(dayofweek=self.parsedict['dayofweek'])

                pt_without_dow = PartialTime.from_object(without_dow)
                relative_pt = p.relative_day_of_week(offset=offset,
                    context=context)

                return pt_without_dow.combine(relative_pt)
            except ValueError:
                pass

        return None

    def expand_ordinal_dow_month(self, context):
        # adapted from Mark Pettit's "Findng the x'th day in a month" 
        # cookbook recipe, seen at
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/425607

        if not (self.parsedict.get('month') and 
                self.parsedict.get('dayofweek')):
            return None

        offset = self.parsedict.get('ordinal')
        if offset is not None:
            offset -= 1

        if self.parsedict.get('relative') == 'last':
            offset = offset or 0
            # last means go from 0 (first) to -1, from 1 (second) to -2
            # (second to last), etc.
            offset += 1
            offset *= -1

        if offset is not None:
            # if year is present, we use it, otherwise, we get it from context
            year = self.parsedict.get('year', context.year)
            month = self.parsedict['month']
            dayofweek = self.parsedict['dayofweek'] - 1
            
            dt = datetime.date(year, month, 1)
            days = [] # list of days with the right dayofweek
            while dt.weekday() != dayofweek:
                dt = dt + datetime.timedelta(days=1)
            while dt.month == month:
                days.append(dt)
                dt = dt + datetime.timedelta(days=7)

            try:
                return PartialTime.from_object(days[offset])
            except IndexError:
                pass

        return None

# TODO mostly replaced with PartialTime.is_valid
def pieces_compatible(piece1, piece2):
    (parsetype1, val1) = piece1
    (parsetype2, val2) = piece2
    if parsetype1 == parsetype2:
        if 'hint' in parsetype1 or parsetype1 == 'int':
            return True
        else:
            return False
    else:
        if parsetype1 in ('time', 'hour') and parsetype2 == 'ampm':
            if parsetype1 == 'hour':
                hour = val1
            else:
                hour = val1.hour

            if val2.upper() == 'PM' and hour < 12:
                return False
            elif val2.upper() == 'AM' and hour > 12:
                return False
            else:
                return True
        else:
            return True

def cartesianproduct(lists, keep_func=None, allow_empty_column=True):
    """Given a list of lists, computes the cartesian products.  In other
    words, if our lists are (A, B, C), A=1,2,3, B=4,5,6, C=7,8,9, we will
    compute all products of the list: (1, 4, 7), (1, 4, 8), ... (3, 6, 9)

    keep_func is a function for pruning that tells use if we want to
    keep a product.  It is called on a sequence of items in the list
    and returns a boolean.
    
    allow_empty_column means that we can optionally omit a list, making
    this function more like an ordered power set."""
    if len(lists) == 0:
        return []
    elif len(lists) == 1:
        singletons = [(piece,) for piece in lists[0]]
        if keep_func and singletons:
            singletons = [singleton for singleton in singletons if
                keep_func(singleton)]
        return singletons
    else: # 2+ items
        tail_product = cartesianproduct(lists[1:], keep_func)
        if allow_empty_column:
            tail_product.append(()) # optionally, don't use any tails
        heads = lists[0]
        all = tail_product[:]
        for tail in tail_product:
            for head in heads:
                newseq = (head,) + tail
                if keep_func(newseq):
                    all.append(newseq)

        return all

class Parse:
    """The main interface to Eventually.  Given text and an optional
    context, parses the text into segments (accessible under the
    attribute segments)."""
    def __init__(self, text, context=None):
        self.segments = []
        self.context = context

        cur_segment = Segment(parseobj=self)
        charnum = 0
        for linenum, line in enumerate(text.splitlines()):
            if cur_segment:
                # new segment since segments don't span lines (they may get
                # recombined later)
                self.segments.append(cur_segment)
                cur_segment = Segment(parseobj=self)
            colnum = 0
            wordnum = 0
            for word in ws_split.split(line):
                # empty words really mean space
                if not word:
                    colnum += 1
                    charnum += 1
                    continue

                p = ParsedWord(word, linenum, colnum, wordnum, charnum)
                if p.parses:
                    cur_segment.append(p)
                elif cur_segment:
                    self.segments.append(cur_segment)
                    cur_segment = Segment(parseobj=self)
                colnum += len(word) + 1
                charnum += len(word) + 1
                wordnum += 1

        if cur_segment:
            self.segments.append(cur_segment)

if __name__ == "__main__":
    import fileinput
    segments = parse(fileinput.input())
    for segment in segments:
        segment.valid_parses()
