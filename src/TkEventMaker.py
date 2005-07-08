import Tix as Tk
from dispatch import dispatcher
import NLTime
from TkTime import TkTimeWithContext
from Utility import make_attributes_from_args

bin_names = ("DateTime", "Date", "Time")

class Bin(Tk.Frame):
    def __init__(self, master, name, contents):
        Tk.Frame.__init__(self, master)
        make_attributes_from_args('name', 'contents')

        self.button = Tk.Button(self, text=name)
        self.button.pack(side='left')
        self.combo = Tk.ComboBox(self)
        self.combo.pack(side='left')
        self.pack(side='left')

        self.listbox = self.combo.slistbox.listbox
        self.strings_to_parse = {}
    def draw(self):
        self.listbox.delete(0, 'end')
        for parse, score in self.contents:
            s = str(parse)
            self.combo.append_history(s)
            self.strings_to_parse[s] = parse

        if self.contents:
            self.pack(side='left')
            self.combo.pick(0)
        else:
            self.pack_forget()
    def select(self, selection):
        # not used yet
        print "selected", self.strings_to_parse.get(selection)

class TkEventMaker(TkTimeWithContext):
    def __init__(self, master):
        TkTimeWithContext.__init__(self, master)
        dispatcher.connect(self.reset_bins, "new parses", sender=self.tktime)
        dispatcher.connect(self.new_segment_parses, "new segment parses", 
            sender=self.tktime)
        dispatcher.connect(self.draw_bins, "no parses", sender=self.tktime)

        self.bins = {} # name : Bin object
        self.bins_sorted = []
        for name in bin_names:
            b = Bin(self, name=name, contents=[])
            self.bins[name] = b
            self.bins_sorted.append(b)
    def reset_bins(self):
        for bin in self.bins.values():
            bin.contents = []
    def new_segment_parses(self, segment, parses):
        for parse, score in parses:
            for bin_name in bin_names:
                bin = self.bins[bin_name]
                method = getattr(parse, "as_%s" % bin_name.lower())
                result = method()
                if result:
                    bin.contents.append((result, score))
                    break
        self.draw_bins()
    def draw_bins(self):
        for bin in self.bins_sorted:
            bin.contents = NLTime.sortedtimes(bin.contents)
            bin.draw()

if __name__ == "__main__":
    root = Tk.Tk()
    root.title("EventMaster 6000")
    tktimewithcontext = TkEventMaker(root)
    tktimewithcontext.pack(fill='both', expand=1)
    Tk.mainloop()
