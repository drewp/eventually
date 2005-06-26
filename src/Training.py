from __future__ import generators

"""a layer on top of NLTime (hiding most of the interface of NLTime)
that helps you find corrections to the parsing and stores those
corrections for future parses of the same text"""

# what if user corrects the same range twice?

# what if Parse changes its answer on the correction? should i store
# the actual answer at the time of saveCorrection?

from NLTime import Parse

class TrainingStore:
    def __init__(self, filename):
        pass

class TrainedParse:

    """a Parse that listens to your corrections, and always uses the
    corrections when asked to parse the same text again"""
    
    def __init__(self, store, text, context=None):
        self.parse = Parse(text, context)
        self.context = context
        self.hidden_ranges = []
        self.corrections = {} # (s,e) : newtime

    def parsedRanges(self):
        """get the times from the text as a list of ((start,end), time)"""
        ranges = []
        for seg in self.parse.segments:
            s,e = seg.extent(charindices=True)
            tm = seg.valid_parses(self.context)[0][0]
            if (s,e) in self.hidden_ranges:
                continue
            if (s,e) in self.corrections:
                p = Parse(self.corrections[(s,e)], self.context)
                tm = p.segments[0].valid_parses(self.context)[0][0]
            ranges.append(((s,e), tm))
        return ranges

    def tryText(self, new_text):
        """parse new_text under the same context as the original text
        to see what date new_text would make. Nothing is stored when
        you call tryText"""

    def saveCorrection(self, (start,end), new_text, old_range=(None,None)):
        
        """The given range of the text should have parsed as if it was
        new_text. From now on, (start,end) will parse as if it was
        new_text. If (start,end) is a correction of an existing range,
        pass the old one as old_range to suppress that parse in the
        future.  """
        if old_range != (None,None):
            self.hidden_ranges.append(old_range)
        self.corrections[(start,end)] = new_text

def trainedParseFactory(store):
    """
    trainedParse = trainedParseFactory(TrainingStore('mystore.dat'))
    result1 = trainedParse(text1)
    result2 = trainedParse(text2)
    """
    return lambda t,c=None: TrainedParse(store,t,c)
