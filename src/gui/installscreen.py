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

from multiprocessing import Queue


import os
from time import sleep

import requests
import kivy
from arma.arma import Arma
from gui.messagebox import MessageBox

from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.logger import Logger

from view.errorpopup import ErrorPopup
from sync.modmanager import ModManager
from sync.modmanager import get_mod_descriptions
from sync.httpsyncer import HttpSyncer
from sync.mod import Mod
from utils.primitive_git import get_git_sha1_auto
from utils.process import Process
from utils.process import Para


class InstallScreen(Screen):
    """
    View Class
    """
    def __init__(self, **kwargs):
        super(InstallScreen, self).__init__(**kwargs)

        self.statusmessage_map = {
            'moddescdownload': 'Retreiving Mod Descriptions',
            'checkmods': 'Checking Mods',
            'moddownload': 'Retreiving Mod',
            'syncing': 'Syncing Mods'
        }

        self.controller = Controller(self)

class Controller(object):
    def __init__(self, widget):
        super(Controller, self).__init__()
        self.view = widget
        self.mod_manager = ModManager()
        self.loading_gif = None
        self.mods = None

        self.arma_executable_object = None

        # status flag whenever a sync was resolved
        self.sync_resolved = False
        self.sync_rejected = False

        # download mod description
        self.para = self.mod_manager.prepare_and_check()
        self.para.then(self.on_checkmods_resolve, self.on_checkmods_reject,
            self.on_checkmods_progress)

        Clock.schedule_interval(self.check_install_button, 0)
        Clock.schedule_once(self.update_footer_label, 0)
        Clock.schedule_interval(self.check_play_button, 1)

    def check_play_button(self, dt):
        if self.arma_executable_object is None:
            return

        returncode = self.arma_executable_object.poll()
        if returncode is None:  # The game has not terminated yet
            return

        print 'Arma has terminated with code: {}'.format(returncode)
        # Allow the game to be run once again.
        self.view.ids.install_button.disabled = False
        self.arma_executable_object = None

    def update_footer_label(self, dt):
        git_sha1 = get_git_sha1_auto()
        footer_text = 'Build: {}'.format(git_sha1[:10] if git_sha1 else 'N/A')
        self.view.ids.footer_label.text = footer_text

    def check_install_button(self, dt):
        if 'install_button' in self.view.ids:
            self.on_install_button_ready()
            return False

    def on_install_button_ready(self):
        self.view.ids.install_button.text = 'Checking'
        self.view.ids.install_button.enable_progress_animation()

    def on_install_button_release(self, btn):
        # do nothing if sync was already resolved
        # this is a workaround because event is not unbindable, see
        # https://github.com/kivy/kivy/issues/903
        if (self.sync_resolved or self.sync_rejected) == True:
            return

        self.view.ids.install_button.disabled = True
        self.para = self.mod_manager.sync_all()
        self.para.then(self.on_sync_resolve, self.on_sync_reject, self.on_sync_progress)
        self.view.ids.install_button.enable_progress_animation()

    def on_checkmods_progress(self, progress, speed):
        self.view.ids.status_image.hidden = False
        self.view.ids.status_label.text = progress['msg']

    def on_checkmods_resolve(self, progress):
        Logger.debug('InstallScreen: checking mods finished')
        self.view.ids.install_button.disabled = False
        self.view.ids.status_image.hidden = True
        self.view.ids.status_label.text = progress['msg']
        self.view.ids.install_button.disable_progress_animation()
        self.view.ids.install_button.text = 'Install'

        Logger.debug('InstallScreen: got mods:')
        for mod in progress['mods']:
            Logger.info('InstallScreen: {}'.format(mod))

        self.mods = progress['mods']

    def on_checkmods_reject(self, progress):
        self.view.ids.install_button.disabled = False
        self.view.ids.status_image.hidden = True
        self.view.ids.status_label.text = progress['msg']
        self.view.ids.install_button.disable_progress_animation()
        self.view.ids.install_button.text = 'Play!'

        ep = ErrorPopup(stacktrace=progress['msg'])
        ep.open()

    def on_sync_progress(self, progress, percentage):
        Logger.debug('InstallScreen: syncing in progress')
        self.view.ids.install_button.disabled = True
        self.view.ids.status_image.hidden = False
        self.view.ids.status_label.text = progress['msg']
        self.view.ids.progress_bar.value = percentage * 100

        # This should be removed and reimplemented once the ParaAll is implemented
        finished = progress.get('workaround_finished')
        if finished == '@task_force_radio':
            text = """Task Force Arrowhead Radio has been downloaded or updated.

Automatic installation of TFR is not yet implemented.
To finish the installation of TFR, you need to go to:

C:\Users\<user>\Documents\TacBF Launcher\mods\@task_force_radio

and:
1) Copy the TeamSpeak3 Client\plugins files to your Teamspeak directory.
2) Enable the TFR plugin in Settings->Plugins in Teamspeak."""

            tfr_info = MessageBox(text, title='Action required!')
            tfr_info.open()

    def on_sync_resolve(self, progress):
        Logger.info('InstallScreen: syncing finished')
        self.sync_resolved = True
        self.view.ids.install_button.disabled = False
        self.view.ids.status_image.hidden = True
        self.view.ids.status_label.text = progress['msg']
        self.view.ids.install_button.disable_progress_animation()

        # switch to play button and different handler
        self.view.ids.install_button.text = 'Play!'
        self.view.ids.install_button.bind(on_release=self.on_play_button_release)

    def on_sync_reject(self, progress):
        Logger.info('InstallScreen: syncing failed')
        self.sync_rejected = True

        self.view.ids.install_button.disabled = False
        self.view.ids.status_image.hidden = True
        self.view.ids.status_label.text = progress['msg']
        self.view.ids.install_button.disable_progress_animation()

        # switch to play button and diffrent handler
        self.view.ids.install_button.text = 'Play!'
        self.view.ids.install_button.bind(on_release=self.on_play_button_release)

        ep = ErrorPopup(stacktrace=progress['msg'])
        ep.open()

    def on_play_button_release(self, btn):
        Logger.info('InstallScreen: User hit play')

        # TODO: Move all this logic somewhere else
        settings = kivy.app.App.get_running_app().settings
        mod_dir = settings.get_launcher_moddir()  # Why from there? This should be in mod.clientlocation but it isn't!

        mods_paths = []
        for mod in self.mods:
            mod_full_path = os.path.join(mod_dir, mod.foldername)
            mods_paths.append(mod_full_path)

        self.arma_executable_object = Arma.run_game(mod_list=mods_paths)
        self.view.ids.install_button.disabled = True