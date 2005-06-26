
import sys, os, unittest, tempfile
sys.path.append(os.path.join(os.path.dirname(__file__),"..","src"))
from Training import TrainingStore, TrainedParse, trainedParseFactory
from PartialTime import PartialTime

class PassThru(unittest.TestCase):
    def test(self):
        parse = TrainedParse(None, "the time is 3pm")
        pr = list(parse.parsedRanges())
        self.assertEqual(len(pr),1)
        self.assertEqual(pr[0], ((12,15), PartialTime(hour=15)))

class WithStore(unittest.TestCase):
    def setUp(self):
        f = tempfile.NamedTemporaryFile(prefix='eventually_train')
        self.filename = f.name
        self.tp = trainedParseFactory(TrainingStore(f.name))

    def tearDown(self):
        try:
            os.remove(self.filename)
        except OSError:
            pass

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

    def testRangeChange(self):
        p = self.tp("the event runs from 1-2")
        p.saveCorrection((20,21), "13:00", old_range=(15,23))
        p.saveCorrection((22,23), "14:00", old_range=(15,23))
        pr = p.parsedRanges()
        self.assertEqual(pr,
                         [((20, 21), PartialTime(hour=13)),
                          ((22, 23), PartialTime(hour=14))])

    def testSave(self):
        p = self.tp("noonish")
        p.saveCorrection((0,7), "noon")

        p2 = self.tp("noonish")
        pr = p2.parsedRanges()
        self.assertEqual(pr[0], ((0,7), PartialTime(hour=12)))


if __name__ == '__main__':
    import unittest
    unittest.main()
