"""Create a dialog to collect imap server and folder details."""

import tkinter as tk
from tkinter import ttk


__version__ = "0.1.0"


class App(ttk.Frame):   # pylint: disable=too-many-ancestors
    """
    Frame sits inside a Tk() root to collect email server info.

    Parameter:

        master: tkinter.Tk() object to contain this Frame.
        callback:  zero-argument function to respond to Submit button.

    Returns a mapping-like object linking label names to string values.
    """

    PORT_IMAP4 = '143'
    PORT_IMAP4_SSL = '993'

    labels = [
        "Server",
        "Port",
        "User name",
        "Password",
        "Folder name",
    ]

    def __init__(self, master, callback, *args, **kwargs):
        super().__init__(master=master, *args, **kwargs)

        master.resizable(False, False)

        # frame to hold the fields
        form_frame = ttk.Frame(relief=tk.SUNKEN, borderwidth=3)
        form_frame.pack(fill=tk.X)

        label_width = max(len(label) for label in self.labels)

        self.form_rows = {name: FormRow(form_frame, label_width, name)
                          for name in self.labels
                          }

        # customise the Port and Password fields
        # self.form_rows['Port'].text = self.PORT_IMAP4_SSL
        self["Port"].text = self.PORT_IMAP4_SSL
        self['Password'].set_password()

        # frame to hold the buttons
        buttons_frame = ttk.Frame(relief=tk.FLAT)
        buttons_frame.pack(fill=tk.X, ipady=2)

        self.submit = ttk.Button(master=buttons_frame, text="Submit",
                                 command=callback
                                 )
        self.cancel = ttk.Button(master=buttons_frame, text="Cancel",
                                 command=self.master.destroy
                                 )
        for button in (self.cancel, self.submit):
            button.pack(side=tk.RIGHT, padx=10, ipadx=10)

        # set Cancel button to respond to Esc key
        self.master.bind("<KeyPress-Escape>",
                         lambda e: self.cancel.invoke()
                         )

        # set focus to the first row
        self.form_rows['Server'].focus_force()

    def disable_submit(self, disable):
        """Set state of submit button to disabled or not."""
        state = ("" if disable else "!") + "disabled"
        self.submit.state((state,))

    def as_dict(self):
        """Return field values as python dictionary."""
        return {k: self[k].text for k in self.labels}

    def __getitem__(self, fieldname):
        return self.form_rows[fieldname]


class FormRow():
    """One row on a form with a label and a text entry widget."""
    def __init__(self, master, label_width, label_text):
        self.frm = ttk.Frame(master=master)
        self.frm.pack(fill=tk.X, ipady=2, expand=True)

        self.lbl = ttk.Label(master=self.frm,
                             width=label_width,
                             text=label_text)
        self.lbl.pack(side=tk.LEFT)

        self.content = tk.StringVar()
        self.txt = ttk.Entry(master=self.frm, textvariable=self.content)
        self.txt.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn = None

    def _set_content(self, textvalue):
        self.content.set(textvalue)

    def _get_content(self):
        return self.content.get()

    text = property(_get_content, _set_content,
                    doc="Text value of entry widget"
                    )

    def set_password(self):
        """Add a button to reveal/ hide password chars."""
        def toggle():
            if self.txt["show"] == "":
                # button is pressed, put it back to normal
                show, state = "\u2022", '!pressed'
            else:
                show, state = "", 'pressed'
            self.txt['show'] = show
            self.btn.state((state,))

        self.btn = ttk.Button(master=self.frm,
                              # bitmap='info',
                              text="\u2714",
                              command=toggle)
        self.btn.pack(side=tk.LEFT, expand=False)
        toggle()

    def focus_force(self):
        """Set focus to this widget."""
        self.txt.focus_force()
