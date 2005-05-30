import Tix as Tk
# TODO: more docs
#       there are some bugs with delete_last_word, delete_word

class BetterTextMixin:
    """Currently a set of better keybindings and a new method (has_text)
    for a Tk Text widget."""
    def __init__(self, text):
        self.text = text

        for evname in "<Prior> <Next> <Home> <End>".split():
            self.text.bind(evname, self.scroll_text)

        # Shift-BackSpace is really called "Terminate_Server"
        # we convert this to a real backspace
        self.text.bind('<Terminate_Server>', self.convert_backspace)
        self.text.bind('<Control-BackSpace>', self.delete_last_word)
        self.text.bind('<Control-w>', self.delete_last_word)
        self.text.bind('<Alt-b>', lambda e: self.move_one_word(backwards=1))
        self.text.bind('<Alt-f>', lambda e: self.move_one_word(backwards=0))
        self.text.bind('<Alt-d>', self.delete_word)

    def scroll_text(self, event):
        """This is the callback for several events involving scrolling
        (either in a relative or absolute fashion).  It performs
        yviews."""
        if event.keysym in ('Home', 'End'):
            target = 1
            if event.keysym == 'Home':
                target = 0

            self.text.yview("moveto", target)
        else:
            direction = 1
            amount = 1
            units = "pages"
            if event.keysym in ('Up', 'Prior'):
                direction = -1
            if event.keysym in ('Up', 'Down'):
                numlines = 2
                units = "units" # UNITS = lines in this case

            self.text.yview("scroll", direction * amount, units)
    
    def find_word_backwards(self):
        """Finds the index of a word boundary before the insert cursor."""
        boundary = "0.0"
        index = self.text.search('([\s\-\/\.])\S', 'insert', backwards=1, 
            regexp=1, stopindex=boundary)
        if not index:
            index = boundary
        return index
    def find_word_forwards(self):
        """Finds the index of a word boundary after the insert cursor."""
        boundary = "end"
        if self.text.index('insert + 1 chars') == self.text.index(boundary):
            return boundary
        index = self.text.search('([\s\-\/\.])\S', 'insert + 1 chars', 
            forwards=1, regexp=1, stopindex=boundary)
        if not index:
            index = boundary
        return index
    def move_one_word(self, backwards=0):
        if backwards:
            index = self.find_word_backwards()
        else:
            index = self.find_word_forwards()

        self.text.mark_set('insert', index)
        self.text.see('insert')
    def delete_word(self, event):
        """Delete from the current position to the next end of word.
        Just like emacs's Alt-d (hopefully)"""
        self.text.delete('insert', self.find_word_forwards())
        self.text.see('insert')
    def delete_last_word(self, event):
        """deletes the word before the insert cursor. the word
        separators are meant to be unsurprising to users of
        emacs. tk's words and shell words are 'bigger' (fewer
        separators). """
        # find the word separator before the insert cursor
        start = self.find_word_backwards()
        if start == "0.0":
            # delete from start of text
            self.text.delete("0.0","insert")
        else:
            # delete from after that separator until the insert cursor
            self.text.delete("%s + 1 chars" % start, 'insert')
        self.text.see('insert')
        return "break"
    def convert_backspace(self, evt):
        """For some reason, Shift-BackSpace has the keysym Terminate_Server.
        We block this event and generate a real BackSpace one instead."""
        self.text.event_generate('<BackSpace>')
        return "break"

    def has_text(self):
        """Returns whether there is any non-whitespace text present."""
        text = self.text.get('0.0', "end")
        return text.strip()

    def is_all_text_visible(self):
        """Returns whether all text is visible in a Tk.Text.  The widget must
        be update()d before this is called in order to be accurate."""
        begin_visible = self.text.bbox("0.0")
        end_visible = self.text.bbox("end - 1c")
        return begin_visible and end_visible


class AutoscrollbarText(Tk.ScrolledText, BetterTextMixin):
    def __init__(self, *args, **kw):
        Tk.ScrolledText.__init__(self, *args, **kw)
        BetterTextMixin.__init__(self, self.text)

        self.text.bind("<KeyRelease>", 
            lambda event: self.auto_y_scrollbar())
        self.text.bind("<<Paste>>", 
            lambda event: self.text.after(50, self.auto_y_scrollbar))
        self.text.bind("<<PasteSelection>>", 
            lambda event: self.text.after(50, self.auto_y_scrollbar))

        # we use a combination of Visibility and Expose to tell us about
        # resizes
        self.bind("<Visibility>", 
            lambda event: self.auto_y_scrollbar())
        self.bind("<Expose>", 
            lambda event: self.auto_y_scrollbar())
    def auto_y_scrollbar(self):
        """Emulates -scrollbar "auto -x" (automatic Y, don't show X)
        since Tk.Text doesn't seem to want to do that for us.  This means
        we show the scrollbar if we can't see the beginning or the end."""
        self.text.update()
        if self.is_all_text_visible():
            self['scrollbar'] = 'none'
        else:
            self['scrollbar'] = 'y'

class AutoexpandText(Tk.Text, BetterTextMixin):
    def __init__(self, *arg, **kwarg):
        self.height_boundaries = kwarg.pop('height_boundaries', (1, None))
        Tk.Text.__init__(self, *arg, **kwarg)
        BetterTextMixin.__init__(self, self)

        self.bind("<KeyRelease>", self.expand_height)
        self.bind("<<Paste>>", 
            lambda event: self.after(50, self.expand_height, event))
        self.bind("<<PasteSelection>>", 
            lambda event: self.after(50, self.expand_height, event))

        self.expand_height()
    def expand_height(self, evt=None):
        """Adjusts the height of this widget to fit the text inside.
        If it thinks that a line was removed, (via Delete or a similar
        action) it will shrink the height to the smallest possible length.
        Unfortunately, Tk won't tell us the real length of the wrapped lines
        (i.e. one really long wrapped line could take up 3 lines on screen).
        To compensate, we use bbox to see if the beginning and end are
        visible and repeatedly increases height until both are visible."""
        if evt:
            keysym = evt.keysym
            if evt.state & 4: # ControlMask is 1 << 2 == 4
                event_name = "Control-" + keysym
            elif evt.state & 8: # Alt is Mod1, Mod1Mask is 1 << 3 == 8
                event_name = "Alt-" + keysym
            elif evt.state & 512: # Mouse button 3
                event_name = "Paste"
            else:
                event_name = keysym

        else:
            event_name = 'Manual'

        minheight, maxheight = self.height_boundaries
        # TODO: we should check to see if they are near the ends before
        #       doing this resize, since it's flashy
        # these keys can decrease the number of lines visible and force
        # us to shrink the size of the
        if event_name in ('Delete', 'BackSpace', 'Return', 'Control-x', 
                      'Control-k', 'Control-w', 'Control-d', 'Alt-d',
                      'Control-BackSpace', 'Paste', 'Manual'):
            text = self.get("0.0", 'end')
            lines = text.splitlines()
            height = max(len(lines), minheight)
            if maxheight is not None:
                height = min(height, maxheight)
            self.configure(height=height)
            self.update() # necessary or else bbox (is_all_text_visible)
                          # won't notice the change

        # now we keep incrementing the height until we can see everything.
        # this causes flashing, so we avoid it as much as possible
        while not self.is_all_text_visible():
            # increment height but keep boundaries
            height = max(int(self['height']) + 10, minheight)
            if maxheight is not None:
                height = min(height, maxheight)
            if height == int(self['height']): # we've hit the boundary
                break
            self['height'] = height
            self.update() # necessary or else bbox (is_all_text_visible)
                          # won't notice the change

if __name__ == "__main__":
    root = Tk.Tk()

    if 0:
        t = AutoexpandText(root, height_boundaries=(10, 20))
    elif 1:
        t = AutoscrollbarText(root)
    else:
        # one way to get better behavior without inheritance
        t = Tk.ScrolledText(root, scrollbar='none')
        BetterTextMixin(t.text)
    
    t.pack(fill='both', expand=0)

    Tk.mainloop()
