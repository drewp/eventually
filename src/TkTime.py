import Tix as Tk
import NLTime
from BetterText import AutoscrollbarText
from Utility import Symbol
from dispatch import dispatcher

import md5
def getsignature(contents):
    return md5.md5(contents).digest()

NotPresent = Symbol('(Not Present)')

class TkTime(AutoscrollbarText):
    def __init__(self, master, **kw):
        kw.setdefault('font', 'Courier 12')
        self.special_symbols = kw.pop('special_symbols', [])
        self.time_context = kw.pop('context', None)
        self.selected_color = kw.pop('selected_color', 'red')
        self.parsed_color = kw.pop('parsed_color', 'lightblue')
        self.unparsed_color = kw.pop('unparsed_color', 'pink')
        AutoscrollbarText.__init__(self, master)
        self.text.config(**kw)

        self.last_sig = None
        self.scheduled_update = None
        self.text.bind('<KeyRelease>', self.sched_update, '+')
        # we have to wait about 50ms since the text won't appear until then
        self.text.bind('<<Paste>>',
            lambda evt: self.after(50, self.update_display), '+')
        self.text.bind('<<PasteSelection>>',
            lambda evt: self.after(50, self.update_display), '+')
        self.text.bind('<ButtonRelease-3>', self.remove_popups)

        self.tags = []
        self.selections = {}
        self.popups = []
    def display_parses(self, text, force_update=False):
        sig = getsignature(text)
        if sig == self.last_sig and not force_update:
            return
        else:
            self.last_sig = sig

        # reset our tags and popup menus
        for tag in self.tags:
            self.text.tag_delete(tag)
        self.popups = []

        self.tags = []
        parse = NLTime.Parse(text, context=self.time_context)
        segments = parse.segments
        dispatcher.send("new parses", segments=segments, sender=self)
        for segmentnum, segment in enumerate(segments):
            valid_parses = segment.valid_parses()
            start, end = segment.extent()
            start = ("%d.%d" % start)
            end = ("%d.%d" % end)
            tag = 'seg%d' % segmentnum
            if valid_parses:
                if self.selections.get(str(segment)):
                    color = self.selected_color
                else:
                    color = self.parsed_color
                self.text.tag_config(tag, background=color, borderwidth=1,
                    relief='raised')
                self.popups.append(self.make_menu(tag, segment, valid_parses))
            else:
                self.text.tag_config(tag, background=self.unparsed_color)
            self.add_tag(tag, start, end)
            dispatcher.send("new segment parses", segmentnum=segmentnum,
                segment=segment, parses=valid_parses, sender=self)
        if not segments:
            dispatcher.send("no parses", sender=self)
    def add_tag(self, tag, start, end):
        self.text.tag_add(tag, start, end)
        self.tags.append(tag)
    def make_menu(self, tag, segment, valid_parses, limit=20):
        popup = Tk.Menu(self, tearoff=0)
        tagnum = int(tag[3:])

        def select(parse):
            if parse is None:
                self.text.tag_config(tag, background=self.parsed_color,
                    borderwidth=1, relief='raised')
            else:
                self.text.tag_config(tag, background=self.selected_color,
                    borderwidth=1, relief='raised')
            # remember our selection
            self.selections[str(segment)] = parse
            dispatcher.send("selection made", segment=segment, selection=parse,
                tag=tag, segmentnum=tagnum, sender=self)

        def hover(mouseisover=False):
            if mouseisover:
                self.text.tag_config(tag, relief='sunken')
            else:
                self.text.tag_config(tag, relief='raised')

        for parse, score in valid_parses[:limit]:
            popup.add_command(label="%s (%s)" % (parse, score),
                command=lambda parse=parse: select(parse))

        for sym in self.special_symbols:
            popup.add_command(label=str(sym), command=lambda: select(sym))
        popup.add_command(label='(Ignore)', command=lambda: select(None))

        def do_popup(event):
            # display the popup menu
            try:
                popup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                popup.grab_release()

        self.text.tag_bind(tag, "<ButtonPress-3>", do_popup)
        self.text.tag_bind(tag, "<Enter>", lambda evt: hover(True))
        self.text.tag_bind(tag, "<Leave>", lambda evt: hover(False))

        return popup
    def remove_popups(self, event):
        """Get rid of all popups"""
        for popup in self.popups:
            popup.unpost()
    def sched_update(self, *args, **kw):
        """Call update_display in the future.  If a call was already
        scheduled, we push it back."""
        force_update = kw.pop('force_update', False)
        if self.scheduled_update:
            self.after_cancel(self.scheduled_update)
        self.scheduled_update = self.after(50, self.update_display,
            force_update)
    def update_display(self, force_update=False):
        self.display_parses(self.text.get('0.0', 'end'), force_update)

class TkTimeWithContext(Tk.Frame):
    def __init__(self, master):
        Tk.Frame.__init__(self, master)
        self.tktime = TkTime(self, bg='black', fg='white',
            insertbackground='white', parsed_color='blue',
            special_symbols=[NotPresent])
        self.tktime.pack(side='top', fill='both', expand=1)

        contextframe = Tk.Frame(self)
        contexttext = Tk.Label(contextframe, text='Context')
        contexttext.pack(side='left', ipadx=0, ipady=0, padx=0, pady=0)
        self.context = TkTime(contextframe)
        dispatcher.connect(self.context_selector, "selection made",
            sender=self.context)
        dispatcher.connect(self.context_has_parses, "new segment parses",
            sender=self.context)
        self.context['height'] = 23 # errr...
        self.context.pack(side='left', fill='x', expand=0)
        self.contextlabel = Tk.Label(contextframe)
        self.contextlabel.pack(side='left', ipadx=0, ipady=0, padx=0, pady=0,
            expand=1)
        contextframe.pack(side='top', fill='both', expand=0)

        self.context.text.bind("<KeyRelease>", self.typed_in_context, '+')
    def context_selector(self, segmentnum, selection):
        if segmentnum == 0:
            self.set_context(selection)
    def set_context(self, context):
        # only set the context if it is fairly interpretable
        if context is None or (context.as_date() or context.as_time()):
            self.tktime.time_context = context
            self.tktime.sched_update(force_update=True)
        if context:
            self.contextlabel['text'] = str(context)
        else:
            self.contextlabel['text'] = ""
    def context_has_parses(self, segmentnum, segment, parses):
        """This is called when the parser has new parses for a segment.
        We set the context to be the first parse from the first segment
        (this, of course, can be manually overridden)."""
        if segmentnum == 0:
            if parses:
                parse, score = parses[0]
                self.set_context(parse)
            else:
                self.set_context(None)
    def typed_in_context(self, *args):
        # if there's no text in the context, set the context to None
        if not self.context.has_text():
            self.set_context(None)

if __name__ == "__main__":
    root = Tk.Tk()
    root.title("TkTime")
    tktimewithcontext = TkTimeWithContext(root)
    tktimewithcontext.pack(fill='both', expand=1)
    Tk.mainloop()
