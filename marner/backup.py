"""Backup

Select a single imap folder
Download entire contents into a mbox folder
Zip the folder
Create a new email with the zip file as an enclosure
Replace it as a new email message in the user INBOX folder

Optionally delete the original folder.
"""


import logging
import tempfile
import pathlib
import imaplib
import email
import mailbox
import zipfile


logger = logging.getLogger(__name__)
DEBUG = True
if DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.debug("Logging started")


class ImapRuntimeError(RuntimeError):
    """Report IMAP protocol error."""


def open_connection(login, verbose=False):
    """Connect to the server."""

    logger.info("Logging into %s: %s", login["hostname"], login["username"])

    if verbose:
        imaplib.Debug = 4

    try:
        conn = imaplib.IMAP4_SSL(login["hostname"], login["port"])
        conn.login(login["username"], login["password"])

    except (OSError, imaplib.IMAP4.error) as err:
        raise ImapRuntimeError(str(err)) from None

    return conn


class GetTempdir:
    """Get the name of a temporary directory."""

    def __init__(self, use_directory=None):
        if not use_directory:
            self.tempdir = tempfile.mkdtemp()
            self.remove_directory = True

        elif not pathlib.Path(use_directory).exists():
            raise FileNotFoundError(
                "Can't find temp directory {}".format(use_directory)
            )

        else:
            self.tempdir = use_directory
            self.remove_directory = False

        logger.info("Temp directory used: %s", self.tempdir)

    def __enter__(self):

        return self.tempdir

    def __exit__(self, exc_type, exc_value, exc_tb):

        if self.remove_directory:
            temp_path = pathlib.Path(self.tempdir)
            for temp_file in temp_path.iterdir():
                temp_file.unlink()
            temp_path.rmdir()

        logger.info("Temp directory %s closed.", self.tempdir)

        return False  # propagate any exception raised.


def make_file_name(directory, folder, extension):
    """Get a legal file name and return a Path object."""

    # replace "/*. " with "_"
    folder_mod = folder.translate({47: 95, 42: 95, 46: 95, 32: 95})

    return pathlib.Path(directory).joinpath(
        folder_mod + (("." + extension) if extension else "")
    )


def get_folder_emails(connection, folder):
    """Generator function: open a connection and yield the folder contents."""

    typ, data = connection.select(folder)
    if typ != "OK":
        raise ImapRuntimeError(
            'Cannot select folder "{}".'.format(folder))

    typ, data = connection.uid("search", None, "ALL")
    if typ != "OK":
        raise ImapRuntimeError("Search failed")

    uid_list = data[0].decode("us-ascii").split()
    logger.debug("Found %d messages to retrieve", len(uid_list))

    for uid in uid_list:

        typ, data = connection.uid("fetch", uid, "(RFC822)")
        if typ != "OK":
            raise ImapRuntimeError("Fetch failed")
        logger.debug("Retrieved message %d.", int(uid))

        yield data[0][1]


def place_message(connection, tempdir, folder_name):
    """Create a new message with zip file, place it in INBOX."""

    zip_path = make_file_name(tempdir, folder_name, "zip")

    logger.debug("Creating EmailMessage.")

    msg = email.message.EmailMessage()
    msg["Subject"] = "Back up email folder"
    msg["From"] = "Self"
    msg["To"] = "Self"
    msg["Date"] = email.utils.formatdate()
    msg.preamble = "Email backup file enclosed: {}".format(zip_path.name)

    maintype, subtype = "application", "zip"

    with open(zip_path, "rb") as zip_contents:

        logger.debug("Creating attachment.")

        msg.add_attachment(
            zip_contents.read(),
            maintype=maintype,
            subtype=subtype,
            filename=zip_path.name,
        )

    logger.debug("Posting message.")

    typ, data = connection.append(
        mailbox="INBOX", flags=None, date_time=None, message=msg.as_bytes()
    )
    if typ != "OK":
        raise RuntimeError("Cannot post message: {!r}".format(data[0]))


def collect_emails(login, folder, use_directory=None):
    """Create a mbox and collect emails into it."""

    with GetTempdir(use_directory) as tempdir:
        logger.debug("Tempdir dir is %s", tempdir)

        mbox_path = make_file_name(tempdir, folder, "mbox")
        logger.debug("Mbox path is %s", mbox_path.as_posix())

        if mbox_path.exists():
            mbox_path.unlink()
        mbox = mailbox.mbox(mbox_path)

        with open_connection(login, verbose=DEBUG) as connection:

            try:
                for eml in get_folder_emails(connection, folder):
                    mess = email.message_from_bytes(eml)
                    mbox.add(mess)
                    logger.debug("Email saved.")

            except ImapRuntimeError as err:
                logger.critical("Saving email failed: %s", err)
                raise

            finally:
                mbox.close()

            zip_path = make_file_name(tempdir, folder, "zip")
            logger.debug("Zipfile path is %s.", zip_path.as_posix())

            if zip_path.exists():
                zip_path.unlink()
            mbox_zip = zipfile.ZipFile(
                zip_path,
                mode="x",
                compression=zipfile.ZIP_BZIP2,
            )
            mbox_zip.write(mbox_path, arcname=mbox_path.name)
            mbox_zip.close()
            logger.debug("Zipfile written.")

            place_message(connection, tempdir, folder)
