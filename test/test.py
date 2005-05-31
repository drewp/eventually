# so it can be run in the repo
import sys
sys.path.append('../src')

from NLTime import parse
from PartialTime import PartialTime
from sets import Set
import datetime

# we try to use the AIMA library, which provides some py2.4 support for
# earlier Pythons
try:
    from AIMA import *
except ImportError:
    pass

# string : list of required results or None
test_cases = {
    "Jan 3rd" : datetime.date(2005, 1, 3),

    """This year's Campus Dance will be held on Friday, May 27 from 9:00 pm
to 1:00 am with Duke Belaire's swing band on the College Green,
student bands on Lincoln Field, and jazz music at Carrie Tower.""" :
        datetime.datetime(2005, 5, 27, 21, 0, 0),

    "FRI JUL 19 2002" : datetime.date(2002, 7, 19),

    # XXX we don't do ranges yet
    "Monday to thursday at 3pm" : None,

    "monday at 3pm" : 1,
    "monday at 3:00pm" : 1,
    "monday at 3:00" : 1,

    """When: friday, may 27, early morning (11am
    where: 252 Ives st""" : (datetime.time(11, 0), datetime.date(2005, 5, 27)),

    # XXX later, we'll try to extract a location maybe
    """SAVE THE DATE---next Monday, May 23, 8pm, for Mira Meyerovich's "good-bye
    for the summer" party!

    It's at my apartment, 203 Camp Street. And no, it's not a surprise, so you
    don't need to be all secretive about it...""" : 
        datetime.datetime(2005, 5, 23, 20, 0),

    """Friday, 03 Jun 05 	Flight DH 1640 	
    Depart: 	Providence, RI (PVD) 	5:04 pm 	
    Arrive: 	Washington-Dulles, VA (IAD) 	6:40 pm

    Sunday, 05 Jun 05 	Flight DH 1633 	
    Depart: 	Washington-Dulles, VA (IAD) 	9:10 pm 	
    Arrive: 	Providence, RI (PVD) 	10:28 pm""" :
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
    for age verification!)""" : None,

    # XXX this is really a range
    """We'll be having a special meeting of BLLIP Fri 5/27 11-1 in CIT345.
    Let's be punctual for once. :)""" : datetime.datetime(2005, 5, 27, 11, 0),
}
# so the test cases have a consistent ordering
test_cases = test_cases.items()
test_cases.sort()

verbose = False
ranks = []
failed_tests = 0
for test_case, expected_results in test_cases:
    # we don't have a result for this yet (maybe because the result object
    # hasn't been built yet)
    if not expected_results:
        continue
    # listify the test case if we haven't already
    if not isinstance(expected_results, (list, tuple)):
        expected_results = [expected_results,]

    expected_results = [PartialTime.from_object(res) 
        for res in expected_results]
    unmatched_results = list(expected_results) # a copy that we'll modify

    segments = parse(test_case)
    for segment in segments:
        seg_results = segment.valid_parses()
        if seg_results:
            for rank, (result, score) in enumerate(seg_results[:20]):
                if result in unmatched_results:
                    unmatched_results.remove(result)
                    ranks.append(rank)

    if unmatched_results or verbose:
        if unmatched_results:
            failed_tests += 1
        print "Test case:"
        print repr(test_case)
        print
        for num, segment in enumerate(segments):
            print "Segment %d:" % num
            print str(segment)
            for parsedword in segment:
                print repr(parsedword)

            seg_results = segment.valid_parses()
            if seg_results:
                for result, score in seg_results[:20]:
                    print "%s\t%s" % (score, result),
                    if result in expected_results:
                        print "<=="
                    else:
                        print
                print

        print "Unmatched results:", expected_results
        print "========================="

print "Summary:"
print "Ran %d tests, %d failed." % (len(test_cases), failed_tests)
# this tells us how well it is doing for the answers that it did find
average = sum(ranks) / float(len(ranks))
print "Average rank: %.5f" % average
print "Median rank: %.5f, stddev %.5f" % (median(ranks), 
                                          stddev(ranks, meanval=average))
print "Worst rank: %s" % max(ranks)
