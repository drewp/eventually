from __future__ import nested_scopes
import os, sys, weakref
from gzip import GzipFile

###################
# parsing helpers #
###################

def try_parse_int(val, default=None):
    """Attempt to parse a string as an integer.  If parsing fails,
    the default will be returned."""
    try:
        return int(val)
    except ValueError:
        return default

def try_parse_float(val, default=None):
    """Attempt to parse a string as an integer.  If parsing fails,
    we try again as a float.  If parsing fails again, the default will
    be returned."""
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return default

def try_parse_date(val, default=None):
    """Attempt to parse a string as an date.  If parsing fails in
    recoverable way, as much information about the date as possible will
    be returned.  If the input is not parsable at all, the default will
    be returned."""
    import mx.DateTime
    try:
        return mx.DateTime.Parser.DateTimeFromString(val)
    except:
        return default

###########################
# dictionary manipulation #
###########################

def dictiadd(d1, d2):
    """Add the numeric values of values in two dictionaries together,
    modifying the first argument in place. (Called iadd to be like
    Python's __iadd__ which is the method that does incremental
    addition)."""
    for k, v in d2.items():
        d1.setdefault(k, 0)
        d1[k] += v
    return d1

def countdict_to_pairs(counts, limit=None):
    """Convert a dictionary from { anything : counts } to a list of at
    most 'limit' pairs (or all if limit is None), sorted from highest
    count to lowest count."""
    pairs = [(count, x) for (x, count) in counts.items() if count]
    pairs.sort()
    pairs.reverse() # sort from high to low
    if limit is not None:
        pairs = pairs[:limit]

    return pairs

def dict_subset(d, dkeys, default=0):
    """Subset of dictionary d: only the keys in dkeys.  If you plan on omitting
    keys, make sure you like the default."""
    newd = {} # dirty variables!
    for k in dkeys:
        newd[k] = d.get(k, default)
    return newd

#########
# files #
#########

def sortedfile(filename, mode='r', sortcmd='sort -n'):
    """Returns a file-like object which contains a sorted version of
    filename.  Note that the file-like object returned is a 
    NamedTemporaryFile and will be deleted when it goes out of scope."""
    import pipes, tempfile
    tf = tempfile.NamedTemporaryFile()

    t = pipes.Template()
    t.append(sortcmd, '--')
    t.copy(filename, tf.name)

    return tf

# TODO make this work with bzip2 as well?
def possibly_compressed_file(filename, mode='r'):
    filename = filename.replace('.gz', '')
    gzip_name = "%s.gz" % filename
    if os.path.exists(filename):
        return file(filename, mode)
    elif os.path.exists(gzip_name): # try adding .gz and using GzipFile
        return GzipFile(gzip_name, mode)
    else:
        raise IOError("Can't find file (or compressed version): '%s'" % \
            filename)

def read_file_with_timeout(fileobject, timeout=1):
    """Given a fileobject, we try to read from it.  If it takes longer than
    timeout to read, we raise an IOError."""
    # this is taken from the examples in the documentation for the
    # signal module
    import signal

    def handler(signum, frame):
        raise IOError, "Couldn't read from file object within %s seconds" % \
            timeout

    # Set the signal handler and an alarm to go off
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    result = fileobject.read()
    signal.alarm(0) # Disable the alarm
    return result

#############
# sequences #
#############

# from http://www.hetland.org/python/distance.py
def edit_distance(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a, b = b, a
        n, m = m, n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*m
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

def power_set(seq):
    """Returns the power set of an (indexable) sequence."""
    return seq \
           and power_set(seq[1:]) + [seq[:1] + y for y in power_set(seq[1:])] \
           or [seq]

# TODO the following two functions should be more similar
# also, they should work the same way as the real max and min in terms
# of arguments
def maxwithundef(*args, **kw):
    """Optional keyword argument: undef.  Use this to specify an undefined 
    value.  Any argument with that value will be dropped.  If there are no
    valid arguments, undef is returned.  Default is None."""
    undef = kw.get('undef', None)
    args = [arg for arg in args if arg != undef]
    if not args:
        return undef
    elif len(args) == 1:
        return args[0]
    else:
        return max(*args)

def minwithundef(*args, **kw):
    """Optional keyword argument: undef.  Use this to specify an undefined 
    value.  Any argument with that value will be dropped.  If there are no
    valid arguments, undef is returned.  Default is None."""
    undef = kw.get('undef', None)
    args = [arg for arg in args if arg != undef]
    if not args:
        return undef
    elif len(args) == 1:
        return args[0]
    else:
        return min(*args)

def find_indices_of_unique_items(seq, sorted=True):
    """Return a pair of a list of unique indices and a hash table mapping
    nonunique indices to the first instance of it.  Unclear?  See this
    example:
    
    >>> x = [101, 102, 103, 101, 104, 106, 107, 102, 108, 109]
    >>> find_indices_of_unique_items(x)
    ([0, 1, 2, 4, 5, 6, 8, 9], {3: 0, 7: 1})"""
    vals = {} # item : index
    nonunique = {} # index : originalindex

    for index, elt in enumerate(seq):
        if elt in vals:
            originalindex = vals[elt]
            nonunique[index] = originalindex
        else:
            vals[elt] = index

    keys = vals.values()
    if sorted:
        keys.sort()

    return keys, nonunique

###################
# unfiled for now #
###################

class ondemand(property):
    """A property that is loaded once from a function."""
    def __init__(self, fget, doc=None):
        property.__init__(self, fget=self.get, fdel=self.delete, doc=doc)
        self.loadfunc = fget
        self.values = weakref.WeakKeyDictionary()
    def get(self, obj):
        if obj not in self.values:
            self.load(obj)
        return self.values[obj]
    def load(self, obj):
        self.values[obj] = self.loadfunc(obj)
    def delete(self, obj):
        # XXX this may not be needed any more
        try:
            del self.values[obj]
        except:
            pass

def make_attributes_from_args(*argnames):
    """
    This function simulates the effect of running
      self.foo = foo
    for each of the given argument names ('foo' in the example just
    now). Now you can write:
        def __init__(self,foo,bar,baz):
            make_attributes_from_args('foo','bar','baz')
            ...
    instead of:
        def __init__(self,foo,bar,baz):
            self.foo = foo
            self.bar = bar
            self.baz = baz
            ... 
    """
    callerlocals = sys._getframe(1).f_locals
    callerself = callerlocals['self']
    for a in argnames:
        try:
            setattr(callerself,a,callerlocals[a])
        except KeyError:
            raise KeyError, "Function has no argument '%s'" % a

def make_dict_from_args(*argnames):
    """
    The sequel to the best selling make_attributes_from_args!  Turn your
    arguments into a dictionary.  Takes a list of the names of the arguements
    to convert, returns a dictionary with their names : values.

    def some_function(foo, bar, qux):
        d = make_dict_from_args('foo', 'bar', 'qux')

    d is now:
    { 'foo' : value_of_foo, 'bar' : value_of_bar, 'qux' : value_of_qux }
    """
    callerlocals=sys._getframe(1).f_locals
    d = {}
    for a in argnames:
        try:
            d[a] = callerlocals[a]
        except KeyError:
            raise KeyError, "Function has no argument '%s'" % a
    return d

def dumpobj(o, double_underscores=0):
    """Prints all the object's non-callable attributes.  If double_underscores
    is false, it will skip attributes that begin with double underscores."""
    print repr(o)
    for a in [x for x in dir(o) if not callable(getattr(o, x))]:
        if not double_underscores and a.startswith("__"):
            continue
        try:
            print "  %20s: %s " % (a, getattr(o, a))
        except:
            pass
    print ""

_count = 0 # certainly not thread safe
def trace(func, stream=sys.stdout):
    """Good old fashioned Lisp-style tracing.  Example usage:
    
    >>> def f(a, b, c=3):
    >>>     print a, b, c
    >>>     return a + b
    >>>
    >>>
    >>> f = trace(f)
    >>> f(1, 2)
    |>> f called args: [1, 2]
    1 2 3
    <<| f returned 3
    3

    TODO: print out default keywords (maybe)"""
    name = func.func_name
    global _count
    _count = 0
    def tracer(*args, **kw):
        global _count
        s = ('\t' * _count) + '|>> %s called with' % name
        _count += 1
        if args:
            s += ' args: %r' % list(args)
        if kw:
            s += ' kw: %r' % kw
        print >>stream, s
        ret = func(*args, **kw)
        _count -= 1
        print >>stream, ('\t' * _count) + '<<| %s returned %s' % (name, ret)
        return ret
    return tracer

def get_current_traceback_tuple():
    """Returns a semiformatted traceback of the current exception as a tuple
    in this form:
       (exceptionclass, exceptioninstance, lines_of_string_traceback_lines)"""
    exceptionclass, exceptioninstance, tb = sys.exc_info()
    tb_lines = traceback.format_tb(tb)
    return (exceptionclass, exceptioninstance, tb_lines)

def pretty_time_range(diff, show_seconds=True):
    """Given a number of seconds, returns a string attempting to represent
    it as shortly as possible.
    
    >>> pretty_time_range(1)
    '1s'
    >>> pretty_time_range(10)
    '10s'
    >>> pretty_time_range(100)
    '1m40s'
    >>> pretty_time_range(1000)
    '16m40s'
    >>> pretty_time_range(10000)
    '2h46m'
    >>> pretty_time_range(100000)
    '27h46m'
    """
    diff = int(diff)
    hours = diff / 3600
    diff %= 3600.0
    minutes = int(diff) / 60
    diff %= 60.0
    seconds = int(diff)
    str = ''
    if hours: str = '%sh' % hours
    if minutes: 
        str += '%sm' % minutes
        if show_seconds and not hours and seconds: str += '%ss' % seconds
    if not str:
        if show_seconds: str = '%ss' % seconds
        else: str = '0m'
    return str

class Symbol:
    """Lisp symbols for Python (sort of).  These are like strings but
    used differently (think exception classes vs. string exceptions).
    Two symbols of the same name are equal but not equal to the string
    of their name."""
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.name)
    def __eq__(self, other):
        return self.name == other.name

################
# testing code #
################

def test_find_indices_of_unique_items():
    x = [101, 102, 103, 101, 104, 106, 107, 102, 108, 109]
    print list(enumerate(x))
    print find_indices_of_unique_items(x)

if __name__ == "__main__":
    test_find_indices_of_unique_items()
