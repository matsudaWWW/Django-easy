from telegram.ext import CallbackContext

from bobweb.bob.command import ChatCommand
from bobweb.bob.resources.bob_constants import PREFIXES_MATCHER, fitz
from telegram import Update
import datetime
import pytz


class AikaCommand(ChatCommand):
    def __init__(self):
        super().__init__(
            name='aika',
            regex=r'' + PREFIXES_MATCHER + 'aika',
            help_text_short=('!aika', 'Kertoo ajan')
        )

    def handle_update(self, update: Update, context: CallbackContext = None):
        time_command(update)

    def is_enabled_in(self, chat):
        return chat.time_enabled


def time_command(update: Update):
    date_time_obj = datetime.datetime.now(fitz).strftime('%H:%M:%S.%f')[:-4]
    time_stamps_str = str(date_time_obj)
    reply_text = '\U0001F551 ' + time_stamps_str
    update.effective_message.reply_text(reply_text, quote=False)