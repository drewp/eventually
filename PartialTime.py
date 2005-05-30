import datetime, calendar

from AIMA import every
from Utility import make_attributes_from_args
    
class FuzzyValue:
    def __init__(self, value, direction=None):
        """direction is an operator like "<", "<=", ">=", ">", or None 
        (direction unknown)

        For example, "before 3pm" would mean FuzzyValue(value=3,
        direction="<") in the hour slot while "around 3pm" would have
        a direction=None."""

partialtime_attrs = ('year', 'month', 'day', 'hour', 'minute', 'second',
    'microsecond', 'ampm', 'dayofweek', 'tzinfo')

class PartialTime:
    """Like a datetime.datetime, but allows for incomplete information.
    Values can be integers or FuzzyValues.  PartialTimes are immutable so
    they can be hashed."""
    def __init__(self, year=None, month=None, day=None, hour=None,
        minute=None, second=None, microsecond=None, ampm=None,
        dayofweek=None, tzinfo=None):
        make_attributes_from_args(*partialtime_attrs)
        self._hash_value = None
    def __repr__(self):
        return "PartialTime(" + \
               ', '.join(["%s=%s" % (attr, getattr(self, attr)) 
                    for attr in partialtime_attrs
                    if getattr(self, attr) is not None]) + \
               ")"
    def __str__(self):
        d = self.as_date()
        t = self.as_time()

        if d and t:
            return "%s %s" % (d, t)
        elif d or t:
            return str(d or t)
        else:
            return repr(self)
    def __hash__(self):
        if not self._hash_value:
            items = self.__dict__.items()
            items.sort()
            self._hash_value = hash(tuple(items))
        return self._hash_value
    def __nonzero__(self):
        for attr in partialtime_attrs:
            if getattr(self, attr) != None:
                return True
        else:
            return False
    
    def __eq__(self, other):
        other = PartialTime.from_object(other)
        for attr in partialtime_attrs:
            if attr == 'ampm':
                continue
            if (getattr(self, attr) or 0) != (getattr(other, attr) or 0):
                return False
        else:
            return True

    # TODO autogenerate this method for all operations in getattr
    def __getattr__(self, attr):
        if attr in ('__add__', '__sub__', '__le__', '__lt__', '__eq__', 
                    '__ge__', '__gt__'):
            def func(other, self=self, op=attr):
                self_dt = self.as_datetime()
                other_dt = other.as_datetime()

                if self_dt and other_dt:
                    opfunc = getattr(self_dt, attr)
                    return opfunc(other_dt)
                else:
                    raise TypeError("Insufficient information in the PartialTimes for '-' operation.")
            return func
        else:
            raise AttributeError("No such attribute: %r" % attr)

    """
    def __sub__(self, other):
        self_dt = self.as_datetime()
        other_dt = other.as_datetime()

        if self_dt and other_dt:
            return self_dt - other_dt
        else:
            raise TypeError("Insufficient information in the PartialTimes for '-' operation.")
    """

    def copy(self):
        return PartialTime.from_object(self.__dict__)
    def combine(self, other):
        # TODO FuzzyValues combine differently
        c = self.copy()
        for attr in partialtime_attrs:
            try:
                setattr(c, attr, getattr(self, attr) or getattr(other, attr))
            except AttributeError:
                pass

        return c

    def relative_day_of_week(self, context=None, offset=0):
        """This PartialTime must be just a day of the week (i.e. "this
        Friday", "next Friday"), or a day, optionally with a month ("the
        2nd [of a month]").  offset is in terms of weeks.

        Examples: (context is defined as the current time if left
        unspecified)

        "This Friday" is computed by
        p = PartialTime(dayofweek=calendar.FRIDAY)
        p.relative_day_of_week(offset=0)

        "Next Thursday" is computed by
        p = PartialTime(dayofweek=calendar.THURSDAY)
        p.relative_day_of_week(offset=1)
        
        "Last Monday" is computed by
        p = PartialTime(dayofweek=calendar.MONDAY)
        p.relative_day_of_week(offset=-1)

        context is a PartialTime object.  We return a PartialTime object
        or None."""
        if self.dayofweek:
            offset += 1
            context = context or self.__class__.now()
            contextdate = context.as_date()
            contextdayofweek = contextdate.weekday() + 1
            dayofweekdiff = datetime.timedelta(self.dayofweek - \
                                               contextdayofweek)
            if abs(dayofweekdiff) == dayofweekdiff:
                offset -= 1

            weeks = datetime.timedelta(7) * offset
            return PartialTime.from_object(contextdate + dayofweekdiff + weeks)
        else:
            raise TypeError("This PartialTime must have a dayofweek attribute.")

    def now(cls):
        return cls.from_object(datetime.datetime.now())
    now = classmethod(now)

    def as_dict(self):
        return self.__dict__.copy()
    def as_date(self):
        # datetime.date requires these three arguments
        try:
            return datetime.date(self.year, self.month, self.day)
        except (AttributeError, TypeError):
            return None
    def as_time(self):
        args = []
        for attr in 'hour', 'minute', 'second', 'microsecond':
            val = getattr(self, attr)
            if val is None:
                break
            else:
                args.append(val or 0)
        return datetime.time(*args)
    def as_datetime(self):
        dt = None
        d = self.as_date()
        if d:
            t = self.as_time() or datetime.time()
            dt = datetime.datetime.combine(d, t)

        return dt

    def is_valid(self):
        """Whether this PartialTime makes sense.  Currently, we validate
        (1) whether our dayofweek makes sense given a date
        (2) whether our AM/PM makes sense given a time"""
        if self.dayofweek:
            try:
                year, month, day = self.year, self.month, self.day
                dayofweek = self.dayofweek
                # they're 0-based, we're 1-based
                realdayofweek = self.as_date().weekday() + 1
                if realdayofweek != dayofweek:
                    return False
            except AttributeError:
                pass

        ampm = self.ampm.upper()
        if (ampm and (self.hour < 1 or self.hour > 12)) or \
           (self.hour < 0 or self.hour > 23):
            return False

        if ampm == 'PM' and hour < 12:
            return False
        elif ampm == 'AM' and hour > 12:
            return False

        return True

    def from_object(obj):
        """obj can be a PartialTime, datetime.datetime, datetime.date,
        datetime.time, or dictionary."""
        if isinstance(obj, PartialTime):
            return obj

        d = {}
        for attr in partialtime_attrs:
            try:
                d[attr] = getattr(obj, attr)
                continue
            except AttributeError:
                pass

            try:
                d[attr] = obj[attr]
            except (KeyError, TypeError):
                pass

        pt = PartialTime(**d)
        return pt
    from_object = staticmethod(from_object)

if __name__ == "__main__":
    p = PartialTime(day=7, hour=2)
    print p.copy()

    p = PartialTime(dayofweek=calendar.THURSDAY)
    print 'last', p.relative_day_of_week(offset=-1)
    print 'this', p.relative_day_of_week(offset=0)
    print 'next', p.relative_day_of_week(offset=1)

    a = PartialTime(hour=15, minute=0)
    b = PartialTime(year=2005, month=5, day=31)
    print a.combine(b)
