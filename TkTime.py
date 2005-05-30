import Tix as Tk
import NLTime

import md5
def getsignature(contents):
    return md5.md5(contents).digest()

# TODO extract some of the dumbass paste stuff and move it to a
# new widget, BetterText.  it should include all the smarts from Hiss's
# TkUI Conversation window
class TkTime(Tk.Text):
    def __init__(self, master, *args, **kw):
        kw.setdefault('font', 'Courier 12')
        self.command = kw.pop('command', None)
        self.time_context = kw.pop('context', None)
        self.selected_color = kw.pop('selected_color', 'red')
        self.parsed_color = kw.pop('parsed_color', 'lightblue')
        self.unparsed_color = kw.pop('unparsed_color', 'pink')
        Tk.Text.__init__(self, master, *args, **kw)

        self.last_sig = None
        self.scheduled_update = None
        self.bind('<KeyRelease>', self.sched_update)
        # we have to wait about 50ms since the text won't appear until then
        self.bind('<<Paste>>', 
            lambda evt: self.after(50, self.update_display))
        self.bind('<<PasteSelection>>', 
            lambda evt: self.after(50, self.update_display))
        self.tags = []
    def display_parses(self, text):
        sig = getsignature(text)
        if sig == self.last_sig:
            return
        else:
            self.last_sig = sig

        for tag in self.tags:
            self.tag_remove(tag, '0.0', 'end')

        self.tags = []
        segments = NLTime.parse(text)
        for count, segment in enumerate(segments):
            valid_parses = segment.valid_parses(context=self.time_context)
            start, end = segment.extent()
            start = ("%d.%d" % start)
            end = ("%d.%d" % end)
            # print "segment", count, start, end
            tag = 'seg%d' % count
            if valid_parses:
                self.tag_config(tag, background=self.parsed_color,
                    borderwidth=1, relief='raised')
                self.make_menu(tag, valid_parses)
            else:
                self.tag_config(tag, background=self.unparsed_color)
            self.add_tag(tag, start, end)
    def add_tag(self, tag, start, end):
        self.tag_add(tag, start, end)
        self.tags.append(tag)
    def make_menu(self, tag, valid_parses):
        popup = Tk.Menu(self, tearoff=0)

        def select(parse):
            if parse is None:
                self.tag_config(tag, background=self.parsed_color,
                    borderwidth=1, relief='raised')
            else:
                self.tag_config(tag, background=self.selected_color,
                    borderwidth=1, relief='raised')
            if self.command:
                self.command(int(tag[3:]), parse)

        def hover(mouseisover=False):
            if mouseisover:
                self.tag_config(tag, relief='sunken')
            else:
                self.tag_config(tag, relief='raised')

        for parse, score in valid_parses[:20]:
            # popup.add_command(label=str(parse), command=lambda: select(parse))
            popup.add_command(label="%s (%s)" % (parse, score), 
                command=lambda parse=parse: select(parse))

        popup.add_command(label='(Ignore)', command=lambda: select(None))

        def do_popup(event):
            # display the popup menu
            try:
                popup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                # make sure to release the grab (Tk 8.0a1 only)
                popup.grab_release()

        self.tag_bind(tag, "<Button-3>", do_popup)
        self.tag_bind(tag, "<Enter>", lambda evt: hover(True))
        self.tag_bind(tag, "<Leave>", lambda evt: hover(False))

    def sched_update(self, *args):
        if self.scheduled_update:
            self.after_cancel(self.scheduled_update)
        self.scheduled_update = self.after(50, self.update_display)
    def update_display(self, *args):
        self.display_parses(self.get('0.0', 'end'))

if __name__ == "__main__":

    root = Tk.Tk()
    root.title("TkTime")

    tktime = TkTime(root, bg='black', fg='white', parsed_color='blue')
    tktime.pack(side='top', fill='both', expand=1)

    def context_selector(segment, selection):
        if segment == 0:
            tktime.time_context = selection
            tktime.update_display()
            if selection:
                contextlabel['text'] = "Context: " + str(selection)
            else:
                contextlabel['text'] = "Context"

    contextframe = Tk.Frame(root)
    contextlabel = Tk.Label(contextframe, text='Context')
    contextlabel.pack(side='left', ipadx=0, ipady=0, padx=0, pady=0)
    context = TkTime(contextframe, height=1, command=context_selector)
    context.pack(side='left', fill='both', expand=1)
    contextframe.pack(side='top', fill='both', expand=0)

    Tk.mainloop()
