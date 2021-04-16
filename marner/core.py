"""Core functions to integrate the gui and the backup."""

import logging

from .gui import App, tk
from .backup import collect_emails, ImapRuntimeError


logging.basicConfig(
    level=logging.INFO,
)


def _do_backup():

    app.disable_submit(True)

    dialog_values = app.as_dict()
    server_login = dict(
        hostname=dialog_values["Server"],
        port=dialog_values["Port"],
        username=dialog_values["User name"],
        password=dialog_values["Password"],
    )
    folder = dialog_values["Folder name"]

    try:
        collect_emails(server_login, folder)

    except ImapRuntimeError:
        pass

    app.disable_submit(False)


root = tk.Tk()
app = App(root, callback=_do_backup)
root.mainloop()
