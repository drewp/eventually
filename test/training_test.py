
import sys, os, unittest, tempfile
sys.path.append(os.path.join(os.path.dirname(__file__),"..","src"))
from Training import TrainedParse, trainedParseFactory
from PartialTime import PartialTime

class PassThru(unittest.TestCase):
    def test(self):
        parse = TrainedParse(None, "the time is 3pm")
        pr = list(parse.parsedRanges())
        self.assertEqual(len(pr),1)
        self.assertEqual(pr[0], ((12,15), PartialTime(hour=15)))

class WithStore(unittest.TestCase):
    def setUp(self):
        f = tempfile.NamedTemporaryFile()
        self.tp = trainedParseFactory(f)

    def testNoCorrections(self):
        pr = self.tp("the time is 3pm").parsedRanges()
        self.assertEqual(pr[0], ((12,15), PartialTime(hour=15)))

    def testCorrection(self):
        p = self.tp("the time is 3")
        p.saveCorrection((12,13), "3:00am")
        corrected = p.parsedRanges()[0]
        self.assertEqual(corrected, ((12,13), PartialTime(hour=3)))

    def testTwoCorrections(self):
        p = self.tp("30 or 45 minutes past noon")
        p.saveCorrection((0,2), "12:30")
        p.saveCorrection((6,8), "12:45")
        pr = p.parsedRanges()
        self.assertEqual(pr[0][1], PartialTime(hour=12, minute=30))
        self.assertEqual(pr[1][1], PartialTime(hour=12, minute=45))
        self.assertEqual(pr[0][1], PartialTime(hour=12, minute=30))

if __name__ == '__main__':
    import unittest
    unittest.main()
