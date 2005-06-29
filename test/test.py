# so it can be run in the repo
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__),"..","src"))

from NLTime import Parse
from PartialTime import PartialTime
from sets import Set
import datetime, calendar, optparse

# we try to use the AIMA library, which provides some py2.4 support for
# earlier Pythons
try:
    from AIMA import *
except ImportError:
    pass

def find_next_day_of_week(dayofweek, start):
    while start.weekday() != dayofweek:
        start += datetime.timedelta(days=1)
    return start

now = PartialTime.now()

# string : list of required results
#          or None (no matches expected)
#          or NotImplementedError (skip this test)
test_cases = {
    "Jan 3rd" : datetime.date(2005, 1, 3),

    """This year's Campus Dance will be held on Friday, May 27 from 9:00 pm
to 1:00 am with Duke Belaire's swing band on the College Green,
student bands on Lincoln Field, and jazz music at Carrie Tower.""" :
        datetime.datetime(2005, 5, 27, 21, 0, 0),

    "FRI JUL 19 2002" : datetime.date(2002, 7, 19),

    # XXX we don't do ranges yet
    "Monday to thursday at 3pm" : NotImplementedError,

    "monday at 3pm" : datetime.datetime.combine(
                        find_next_day_of_week(calendar.MONDAY, now).as_date(),
                        datetime.time(15, 0)),
    "monday at 3:00pm" : datetime.datetime.combine(
                        find_next_day_of_week(calendar.MONDAY, now).as_date(),
                        datetime.time(15, 0)),
    "monday at 3:00" : datetime.datetime.combine(
                        find_next_day_of_week(calendar.MONDAY, now).as_date(),
                        datetime.time(15, 0)),


    """When: friday, may 27, early morning (11am
    where: 252 Ives st""" : (datetime.time(11, 0), datetime.date(2005, 5, 27)),

    # XXX later, we'll try to extract a location maybe
    """SAVE THE DATE---next Monday, May 23, 8pm, for Mira Meyerovich's "good-bye
    for the summer" party!

    It's at my apartment, 203 Camp Street. And no, it's not a surprise, so you
    don't need to be all secretive about it...""" : 
        datetime.datetime(2005, 5, 23, 20, 0),

    """Friday, 03 Jun 05        Flight DH 1640  
    Depart:     Providence, RI (PVD)    5:04 pm         
    Arrive:     Washington-Dulles, VA (IAD)     6:40 pm

    Sunday, 05 Jun 05   Flight DH 1633  
    Depart:     Washington-Dulles, VA (IAD)     9:10 pm         
    Arrive:     Providence, RI (PVD)    10:28 pm""" :
        (datetime.date(2005, 6, 3), datetime.time(17, 4), 
         datetime.time(18, 40),
         datetime.date(2005, 6, 5), datetime.time(21, 10), 
         datetime.time(22, 28)),

    """Dear Friends!
    It's time for our annual June party!
    Please join us to eat food, catch up on news, meet new people, swap clothes,
    sit on the deck, visit our cats, hang out, talk, drink, eat more

    When:           Saturday June 11, 1 pm until whenever
    Where:  Nancy and Mark's House
                   3846 La Cresta Ave, Oakland 94602
                   510-530-6412
    Who:            You & anybody else you know
    What:           Please bring clothes for the swap.
                   No need to bring food, we'll have plenty!""" :
        # XXX should be an open ended range "until whatever"
        # should extract location
        datetime.datetime(2005, 6, 11, 13, 0, 0),

    """Following the awarding of undergraduate and graduate degrees
    on Sunday, May 29, a reception will be held for you, your family
    and friends.  Please join us on the 3rd and 4th floors of the CIT
    Building for champagne and hors d'oeuvres.""" :
        datetime.date(2005, 5, 29),

    # XXX this one needs context=datetime.datetime(2005, 5, 23)
    """Happy End of the Semester!

    To coincide with this wondrous occasion, please join me and the GSC
    Board at the Graduate Lounge, Friday night at 6pm for the Annual GSC
    Champagne Toast.  We will be wishing all of our graduating students
    farewell and good luck on the next phase of their lives!  ALL graduate
    students are invited as well as family and friends.  (Please bring ID
    for age verification!)""" : NotImplementedError,

    # XXX this is really a range
    """We'll be having a special meeting of BLLIP Fri 5/27 11-1 in CIT345.
    Let's be punctual for once. :)""" : datetime.datetime(2005, 5, 27, 11, 0),

    """From:    "George B. Loriot" <George_Loriot@Brown.EDU>
    To:      4th Year Students, Graduate Students, Medical Students, 
             All Faculty, Exempt Staff, Non-Exempt Staff
    Subject: Reminder: Scientific Watercooler today at 4:00

    Reminder that the 'Scientific Watercooler', hosted by CCV, we be held
    today (Tuesday, 5/31) at 4:00 in the CIT boardroom.  This month,
    Physics Professor Brad Marston will discus his research on nonlinear
    systems using Objective-C and Apple's Cocoa development environment.
    Details are at the URL below.

    The Scientific Watercoolers are open to the public; anyone with an
    interest in scientific computing is invited to attend.  An informal
    discussion will follow the presentation.""" : 
        datetime.datetime(2005, 5, 31, 16, 0),

    "On 5/27/05, Robert Lynch <robert.ly...@gmail.com> wrote:" :
        datetime.date(2005, 5, 27),

    # XXX another tricky range one
    """ACM SIGGRAPH, SIGCHI and AIGA have announced the 2nd international DUX
    conference, "Designing for User Experiences", will take place 3-5
    November, in San Francisco, CA at the beautiful Fort Mason Center. The San
    """ : NotImplementedError,

    "On May 27, 2005, at 11:08 AM," : datetime.datetime(2005, 5, 27, 11, 8),

    """2005/6/16 night
    2005/6/17 morning, no night
    2005/6/18 night show
    2005/6/19 14:00-23:00 show""" : 
        [datetime.date(2005, 6, 16),
         datetime.date(2005, 6, 17),
         datetime.date(2005, 6, 18),
         # XXX this last one should be a range
         datetime.datetime(2005, 6, 19, 14, 0)],
            
    "29 May 2005 10:05:19 -0700" : datetime.datetime(2005, 5, 29, 10, 5, 19),

    "Delivery estimate: July 19, 2004" : datetime.date(2004, 7, 19),

    "Departs **July 19, 2002** 5:30pm" : datetime.datetime(2002, 7, 19, 17, 30),

    "Smarch 19, 2002 5:30pm" : datetime.time(17, 30),

    "ISSUED OCT 2002" : PartialTime(year=2002, month=10),

    "7:30 a.m." : datetime.time(7, 30),
    "7:30a.m." : datetime.time(7, 30),
    "7:30 p.m." : datetime.time(19, 30),
    "7:30p.m." : datetime.time(19, 30),

    'feb 12 2002' : datetime.date(2002, 2, 12),

    'tomorrow' : now.as_date() + datetime.timedelta(days=1),
    'yesterday' : now.as_date() - datetime.timedelta(days=1),
    'today' : now.as_date(),
    'now' : now,
    'tomorrow at 3pm' : datetime.datetime.combine(now.as_date() + datetime.timedelta(days=1), datetime.time(15, 0)),
    '3pm tomorrow' : datetime.datetime.combine(now.as_date() + datetime.timedelta(days=1), datetime.time(15, 0)),
    '3pm today' : datetime.datetime.combine(now.as_date(), 
                                            datetime.time(15, 0)),

    '11/2000' : PartialTime(year=2000, month=11),
    
    'Wed 06/01' : datetime.date(2005, 6, 1),

    "sunday june 5th" : datetime.date(2005, 6, 5),

    "Friday september 30th" : datetime.date(2005, 9, 30),

    # TODO need to make sure we fix the context to 2005 for these
    "third wed in march 2005" : datetime.date(2005, 3, 16),
    "3rd wed in march 2005" : datetime.date(2005, 3, 16),
    "3rd wed in march" : datetime.date(2005, 3, 16),
    "last wed in march" : datetime.date(2005, 3, 30),
    "first wed in march" : datetime.date(2005, 3, 2),

    "0;" : None,
    "1px" : None,
    "9=20" : None,
    "5.0" : None,
    "+1 (650)" : None,
    "v1.3.90-cvs" : None,
    "$5.95<br>" : None,
    "$5.95" : None,
    "10pt;=20" : None,
}

def report_test(test_case, segments, expected_results, unmatched_results,
                msg="", context=now, filter_incomplete=False):
    print "Test case:"
    print "\t" + repr(test_case)
    for num, segment in enumerate(segments):
        print "\tSegment %d: %r" % (num, str(segment))
        for parsedword in segment:
            print "\t\tNode:", repr(parsedword.originalword)
            for parse in parsedword.parses:
                print "\t\t\t" + str(parse)
        
        seg_results = segment.valid_parses(context, filter_incomplete)
        if seg_results:
            print "\t\tScore\tInterpretation"
            for result, score in seg_results[:20]:
                print "\t\t%s\t%s" % (score, result),
                if result in expected_results:
                    print "<=="
                else:
                    print
        else:
            print "\t\t(no interpretations)"
        print
    
    if unmatched_results:
        print "\tUnmatched results:"
        for result in unmatched_results:
            print '\t' + repr(result)
    if msg:
        print "\t" + msg
    print

def run_tests(opts, test_cases):
    # so the test cases have a consistent ordering
    test_cases = test_cases.items()
    test_cases.sort()
    
    ranks = []
    num_tests_failed = 0
    num_tests_run = 0
    num_segments_failed = 0
    num_segments_run = 0
    for test_case, expected_results in test_cases:
        # we don't have a result for this yet (maybe because the type of the
        # result object hasn't been built yet, e.g. ranges)
        if expected_results is NotImplementedError:
            continue
        
        parse = Parse(test_case)
        segments = parse.segments
        num_tests_run += 1
        
        if expected_results is None:
            num_segments_run += 1
            if some(lambda s: s.valid_parses(now, True), segments):
                num_tests_failed += 1
                num_segments_failed += 1
                if not opts.summary_only:
                    report_test(test_case, segments, [], [],
                                msg="Parse found %s segment(s) but there "
                                "should have been none." % len(segments), 
                                filter_incomplete=True)
            continue
        
        # listify the test case if we haven't already
        if not isinstance(expected_results, (list, tuple)):
            expected_results = [expected_results,]
        
        expected_results = [PartialTime.from_object(res) 
            for res in expected_results]
        unmatched_results = list(expected_results) # a copy that we'll modify
        
        num_segments_run += len(expected_results)
        
        for segment in segments:
            # we don't filter out incomplete parses since some test cases have
            # incomplete answers
            seg_results = segment.valid_parses(context=now, 
                                               filter_incomplete=False)
            if seg_results:
                for rank, (result, score) in enumerate(seg_results[:20]):
                    if result in unmatched_results:
                        unmatched_results.remove(result)
                        ranks.append(rank)
        
        num_segments_failed += len(unmatched_results)
        
        if unmatched_results or opts.verbose:
            if unmatched_results:
                num_tests_failed += 1
            if not opts.summary_only:
                report_test(test_case, segments,
                            expected_results, unmatched_results)
    
    print "Summary:"
    print "Ran %d tests, %d failed." % (num_tests_run, num_tests_failed)
    print "Ran %d segment tests, %d failed." % (num_segments_run, 
                                                num_segments_failed)
    # this tells us how well it is doing for the answers that it did find
    average = sum(ranks) / float(len(ranks))
    print 'Distribution:', ', '.join([str(pair) for pair in histogram(ranks)])
    print "Average rank: %.5f, stddev %.5f" % (average,
                                               stddev(ranks, meanval=average))

parser = optparse.OptionParser()
parser.add_option("-v", "--verbose", action="store_true")
parser.add_option("-s", "--summary-only", action="store_true")
opts,args = parser.parse_args()

run_tests(opts, test_cases)
