# Tactical Battlefield Installer/Updater/Launcher
# Copyright (C) 2015 TacBF Installer Team.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from __future__ import unicode_literals

import sys

from config import config
from kivy.base import ExceptionHandler
from kivy.base import ExceptionManager
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from utils import browser
from utils.primitive_git import get_git_sha1_auto
from utils.critical_messagebox import MessageBox
from utils.testtools_compat import _format_exc_info
from view.chainedpopup import ChainedPopup

DEFAULT_ERROR_MESSAGE = """Critical Error.
If you can't find an answer to your problem [color=3572b0][ref={}]on the troubleshooting page[/ref][/color]
copy the text below and post it on the bugtracker:

[color=3572b0][ref={}]{}[/ref][/color]
""".format(config.troubleshooting_url, config.bugtracker_url, config.bugtracker_url)

POPUP_TITLE = """An error occurred"""
CRITICAL_POPUP_TITLE = """An error occurred. Copy it with Ctrl+C and submit a bug"""


def open_hyperlink(obj, ref):
    browser.open_hyperlink(ref)


class ErrorPopup(ChainedPopup):
    """Show a popup in case an error ocurred.
    Arguments:
    message - The message to be shown in a label.
    details - Shows an additional box containing details that may span dozens of lines.
    """
    def __init__(self, message=DEFAULT_ERROR_MESSAGE, details=None, label_markup=True):
        bl = BoxLayout(orientation='vertical')
        la = Label(text=message, size_hint_y=0.3, markup=label_markup, halign='center')
        la.bind(on_ref_press=open_hyperlink)
        la.text_size = (550, None)  # Enable wrapping when text inside label is over 550px wide
        bl.add_widget(la)

        if details:
            ti = TextInput(text=details, size_hint_y=0.7)
            bl.add_widget(ti)

        super(ErrorPopup, self).__init__(
            title=POPUP_TITLE, content=bl, size_hint=(None, None), size=(600, 400))


def error_popup_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            build = get_git_sha1_auto()
            stacktrace = "".join(_format_exc_info(*sys.exc_info()))
            msg = 'Build: {}\n{}'.format(build, stacktrace)
            # p = ErrorPopup(details=msg)
            # p.open()
            MessageBox(msg, CRITICAL_POPUP_TITLE)

    return wrapper


class PopupHandler(ExceptionHandler):
    def handle_exception(self, inst):
        build = get_git_sha1_auto()
        stacktrace = "".join(_format_exc_info(*sys.exc_info()))
        msg = 'Build: {}\n{}'.format(build, stacktrace)
        p = ErrorPopup(details=msg)
        p.chain_open()
        return ExceptionManager.PASS
