import re, calendar, datetime
from PartialTime import PartialTime
from AIMA import *

"""
Some notes for now:
Based on drewp's design which parsed words into these categories:

             n - number
             y - year
             m - month (including abbreviations)
             d - day-of-week
             t - time-of-day (some parsable time, including ambiguous
                 ones like '7:30')
             u - unknown (the default)

We also have:

             M - AM/PM
             z - timezone
             m - modifier ("next", "last", "this" -- needs a context)
             - - range marker ("-", "to", "until")

And should add:

             U - time unit ('week', 'hour', 'month' -- combine with relative
                 and context)
"""

days_of_week = [day.lower() for day in calendar.day_name]
month_names = [month.lower() for month in calendar.month_name]

nonint_start = re.compile(r'^[^\d]+')
nonint_end = re.compile(r'[^\d]+$')

punc = r'[\.\,;:\'"\(\)]'
punc_re = re.compile(r'%s+' % punc)
punc_start_re = re.compile(r'^%s+' % punc)
punc_end_re = re.compile(r'%s+$' % punc)

ws_split = re.compile(r'\s')

ordinals_re = re.compile(r'st|nd|rd|th', re.I)
time_re = re.compile(r'(\d{1,2})(?:\:?(\d+))?(?:\:?(\d+))?\s*([AP]M)?(?!th)(?!rd)(?!st)', re.I)
# 5/27
# 6.01.2004
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
        if (text in day) or (len(day) < len(text) and day in text):
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
        for month, day, year in ((a, b, c), (b, c, a)):
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
                        y = (y,)
                    results.extend([datetime.date(year, m, d) for year in y])
                elif year: # invalid year portion
                    pass # the date is no good
                else: # missing year portion
                    results.append(PartialTime(month=m, day=d))

        return results or None

def is_int(text):
    # remove trailing non-numbers
    text = nonint_end.sub('', text)
    text = nonint_start.sub('', text)
    try:
        return int(text)
    except ValueError:
        return None

def is_hour(text):
    i = is_int(text)
    if i is not None and not ordinals_re.search(text):
        if 0 <= i <= 11:
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

    match = time_re.search(text)
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
        elif text == 'midnight': # XXX this is broken
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
    if text in ['at', 'from', 'night', 'day']:
        return text

def is_rangehint(text):
    text = text.lower()
    text = punc_re.sub('', text)
    if text in ['-', 'to', 'until']:
        return text

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
    text = text.lower()
    text = punc_re.sub('', text)
    # TODO list more ordinals?
    if text in ['next', 'last', 'this', 'upcoming', 'previous', 'following',
                'first', 'second', 'third', 'fourth', 'fifth']:
        # normalize some of these
        text = text.replace('following', 'next')
        text = text.replace('upcoming', 'this')
        text = text.replace('previous', 'last')

        return text

all_parsers = [is_dayofweek, is_date, is_time, is_month, is_day, is_year,
               is_hour, is_int, is_timehint, is_ampm,
               is_relative, is_lochint, is_locpiece, is_rangehint]

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
    'relative' : 1, 
    'int' : 0, 
    'locpiece' : 1, 
    'lochint' : 1, 
    'timehint' : 1, 
    'rangehint' : 1
}
common_orders = [
    "dayofweek month day year",
    "dayofweek month day",
    "dayofweek day",
    "month year time",
    "month year hour",
    "month year hour minute",
    "month year hour minute ampm",
    "month day",
    "month year",
    "month",
    "year",
    "time",
    'hour minute ampm',
    'hour minute second ampm',
    'hour minute',
    'hour minute second',
]
common_orders = [tuple(order.split()) for order in common_orders]

class ParsedWord:
    def __init__(self, word, lineno=None, colno=None, wordno=None, 
        parsers=None):
        self.originalword = word
        self.lineno = lineno
        self.colno = colno
        self.wordno = wordno
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
        return "<Node %r %d:%d %s>" % (self.originalword, self.lineno, 
                                       self.wordno, str(self.parses))

class Segment(list):
    """A consequtive sequence of ParsedWord objects.  Subclass of a list,
    so all list methods will work."""
    def extent(self):
        """Returns the start and end line:column for this segment."""
        first, last = self[0], self[-1]
        return ((first.lineno + 1, first.colno), 
                (last.lineno + 1, last.colno + len(str(last))))
    def just_hints(self):
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

    def valid_parses(self, context=None):
        """Returns all valid parses and their score, ordered by score.
        ((parse1, score1), (parse2, score2), ...)"""
        # these can be skipped
        if len(self) == 1 and self.just_hints():
            return None

        context = context or PartialTime.now()

        # for node in self:
            # print repr(node)
        
        interpretable_parses = []
        all_parses = cartesianproduct([node.parses for node in self], 
                                      self.all_compatible)
        for interp in all_parses:
            # print "interp", interp
            interp = SegmentInterpretation(interp)
            interp.set_segment(self)
            score, result = interp.score(context)
            # print "score", score
            # print "result", repr(result)
            if score > 0 and result:
                interpretable_parses.append((score, result))

        scores = {} # interp : best score
        for score, interp in interpretable_parses:
            if (interp in scores and score > scores[interp]) or \
               (interp not in scores):
                scores[interp] = score

        # sort by scores then by distance to the context
        # XXX for some reason, this doesn't sort properly
        def sortkey((parse, score)):
            try:
                delta = parse - context
                diff = -abs(delta.seconds)
            except TypeError:
                diff = -1e10
            return (score, diff)
        parses = sorted(scores.items(), key=sortkey, reverse=True)
        return parses

class SegmentInterpretation(tuple):
    def __init__(self, *args):
        tuple.__init__(self, *args)
        self.parsedict = dict(self)
        self.segment = None
    def set_segment(self, segment):
        self.segment = segment
    def grammar_score(self):
        ourorder = tuple([parser for parser, val in self])
        if ourorder in common_orders:
            return 5
        else:
            return 0
    def score(self, context):
        result = self.convert_parse_to_date_and_time(context)
        if not result:
            return (0, result)
        score = self.grammar_score()
        # print "score", self.parsedict, repr(result)
        if 'dayofweek' in self.parsedict and 'month' in self.parsedict:
            if isinstance(result, (datetime.date, datetime.datetime)):
                # print "checking dow"
                try:
                    # they're 0-based, we're 1-based
                    year, month, day = result.year, result.month, result.day
                    # print "ymd", year, month, day
                    dayofweek = self.parsedict['dayofweek']
                    # print "dow", dayofweek
                    realdayofweek = result.weekday() + 1
                    # realdayofweek = calendar.weekday(year, month, day) + 1
                    # print "real", realdayofweek
                    if realdayofweek == dayofweek:
                        score += 40
                    else:
                        return (0, result)
                except AttributeError:
                    pass
            else: # if we have a dayofweek, we better use it
                return (0, result)

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
        if 'month' in self.parsedict:
            if not 'year' in self.parsedict:
                self.parsedict['year'] = context.year
        if 'hour' in self.parsedict:
            if not 'minute' in self.parsedict:
                self.parsedict['minute'] = 0

        # expand 'time' and 'date'
        if 'time' in self.parsedict:
            t = self.parsedict['time']
            try:
                self.parsedict['hour'] = t.hour
                self.parsedict['minute'] = t.minute
                self.parsedict['second'] = t.second
                del self.parsedict['time']
            except AttributeError:
                pass
            
        if 'date' in self.parsedict:
            d = self.parsedict['date']
            try:
                self.parsedict['year'] = d.year
                self.parsedict['month'] = d.month
                self.parsedict['day'] = d.day
                del self.parsedict['date']
            except AttributeError:
                pass

        without_dow = self.parsedict.copy()
        dow = without_dow.pop('dayofweek', None)
        if dow and not (without_dow.get('year') or \
                        without_dow.get('month') or \
                        without_dow.get('day')):
            # if we're just a dayofweek and a rel or just a dayofweek
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

        pt = PartialTime.from_object(self.parsedict)
        return pt

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

def cartesianproduct(lists, keep_func=None):
    if len(lists) == 0:
        return []
    elif len(lists) == 1:
        return [(piece,) for piece in lists[0]]
    else: # 2+ items
        tail_product = cartesianproduct(lists[1:], keep_func)
        tail_product.append(()) # optionally, don't use any tails
        heads = lists[0]
        all = tail_product[:]
        for tail in tail_product:
            for head in heads:
                newseq = (head,) + tail
                if keep_func(newseq):
                    all.append(newseq)

        return all

def parse(text):
    segments = []
    cur_segment = Segment()
    for lineno, line in enumerate(text.splitlines()):
        if cur_segment:
            # new segment per line
            segments.append(cur_segment)
            cur_segment = Segment()
        colno = 0
        wordno = 0
        for word in ws_split.split(line):
            if not word:
                colno += 1
                continue

            p = ParsedWord(word, lineno, colno, wordno)
            if p.parses:
                print repr(p)
                cur_segment.append(p)
            elif cur_segment:
                segments.append(cur_segment)
                cur_segment = Segment()
            colno += len(word) + 1
            wordno += 1

    if cur_segment:
        segments.append(cur_segment)
    return segments

if __name__ == "__main__":
    import fileinput
    segments = parse(fileinput.input())
    for segment in segments:
        segment.valid_parses()
