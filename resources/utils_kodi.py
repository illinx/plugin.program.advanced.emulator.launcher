# -*- coding: utf-8 -*-
#
# Advanced Emulator Launcher
# Copyright (c) 2016-2018 Wintermute0110 <wintermute0110@gmail.com>
# Portions (c) 2010-2015 Angelscry and others
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# -------------------------------------------------------------------------------------------------
# Utility functions which DEPEND on Kodi modules
# -------------------------------------------------------------------------------------------------
# --- Python compiler flags ---
from __future__ import unicode_literals

# --- Python standard library ---
from abc import ABCMeta, abstractmethod
import sys, os, time, random, hashlib, urlparse, json
import xml.etree.ElementTree as ET

# --- Kodi modules ---
try:
    import xbmc, xbmcgui
except:
    from utils_kodi_standalone import *

from filename import *

# --- AEL modules ---
# >> utils_kodi.py must not depend on any other AEL module to avoid circular dependencies.

# --- Constants -----------------------------------------------------------------------------------
LOG_ERROR   = 0
LOG_WARNING = 1
LOG_INFO    = 2
LOG_VERB    = 3
LOG_DEBUG   = 4

# --- Internal globals ----------------------------------------------------------------------------
current_log_level = LOG_INFO
use_print_instead = False

# -------------------------------------------------------------------------------------------------
# Logging functions
# -------------------------------------------------------------------------------------------------
def set_log_level(level):
    global current_log_level

    current_log_level = level

def set_use_print(use_print):
    global use_print_instead

    use_print_instead = use_print

#
# For Unicode stuff in Kodi log see http://forum.kodi.tv/showthread.php?tid=144677
#
def log_debug(str_text):
    if current_log_level >= LOG_DEBUG:
        # If str_text has str type then convert to unicode type using decode().
        # We assume that str_text is encoded in UTF-8.
        # This may fail if str_text is encoded in latin, etc.
        if isinstance(str_text, str): str_text = str_text.decode('utf-8')

        # At this point we are sure str_text is a unicode string.
        log_text = 'AEL DEBUG: ' + str_text
        log(log_text, LOG_VERB)

def log_verb(str_text):
    if current_log_level >= LOG_VERB:
        if isinstance(str_text, str): str_text = str_text.decode('utf-8')
        log_text = 'AEL VERB : ' + str_text
        log(log_text, LOG_VERB)

def log_info(str_text):
    if current_log_level >= LOG_INFO:
        if isinstance(str_text, str): str_text = str_text.decode('utf-8')
        log_text = 'AEL INFO : ' + str_text
        log(log_text, LOG_INFO)

def log_warning(str_text):
    if current_log_level >= LOG_WARNING:
        if isinstance(str_text, str): str_text = str_text.decode('utf-8')
        log_text = 'AEL WARN : ' + str_text
        log(log_text, LOG_WARNING)

def log_error(str_text):
    if current_log_level >= LOG_ERROR:
        if isinstance(str_text, str): str_text = str_text.decode('utf-8')
        log_text = 'AEL ERROR: ' + str_text
        log(log_text, LOG_ERROR)

def log(log_text, level):
    if use_print_instead:
        print(log_text.encode('utf-8'))
    else:
        xbmc.log(log_text.encode('utf-8'), level = xbmc.LOGERROR)

# -------------------------------------------------------------------------------------------------
# Kodi notifications and dialogs
# -------------------------------------------------------------------------------------------------
#
# Displays a modal dialog with an OK button. Dialog can have up to 3 rows of text, however first
# row is multiline.
# Call examples:
#  1) ret = kodi_dialog_OK('Launch ROM?')
#  2) ret = kodi_dialog_OK('Launch ROM?', title = 'AEL - Launcher')
#
def kodi_dialog_OK(row1, row2='', row3='', title = 'Advanced Emulator Launcher'):
    xbmcgui.Dialog().ok(title, row1, row2, row3)

#
# Returns True is YES was pressed, returns False if NO was pressed or dialog canceled.
#
def kodi_dialog_yesno(row1, row2='', row3='', title = 'Advanced Emulator Launcher'):
    ret = xbmcgui.Dialog().yesno(title, row1, row2, row3)

    return ret

#
# Displays a small box in the low right corner
#
def kodi_notify(text, title = 'Advanced Emulator Launcher', time = 5000):
    # --- Old way ---
    # xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % (title, text, time, ICON_IMG_FILE_PATH))

    # --- New way ---
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_INFO, time)

def kodi_notify_warn(text, title = 'Advanced Emulator Launcher warning', time = 7000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_WARNING, time)

#
# Do not use this function much because it is the same icon as when Python fails, and that may confuse the user.
#
def kodi_notify_error(text, title = 'Advanced Emulator Launcher error', time = 7000):
    xbmcgui.Dialog().notification(title, text, xbmcgui.NOTIFICATION_ERROR, time)

#
# NOTE I think Krypton introduced new API functions to activate the busy dialog window. Check that
#      out!
#
def kodi_busydialog_ON():
    xbmc.executebuiltin('ActivateWindow(busydialog)')

def kodi_busydialog_OFF():
    xbmc.executebuiltin('Dialog.Close(busydialog)')

def kodi_refresh_container():
    log_debug('kodi_refresh_container()')
    xbmc.executebuiltin('Container.Refresh')

def kodi_toogle_fullscreen():
    # >> Frodo and up compatible
    xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Input.ExecuteAction", "params":{"action":"togglefullscreen"}, "id":"1"}')

FAVOURITES_PATH = "special://userdata/favourites.xml"

def kodi_read_favourites():
    
    favourites = {}
    favouritesFile = KodiFileName(FAVOURITES_PATH)

    if favouritesFile.exists():
        fav_xml = favouritesFile.readXml()
        fav_elements = fav_xml.findall( 'favourite' )
        for fav in fav_elements:
            try:
                fav_icon = fav.attrib[ 'thumb' ].encode('utf8','ignore')
            except:
                fav_icon = "DefaultProgram.png".encode('utf8','ignore')

            fav_action = fav.text.encode('utf8','ignore')
            fav_name = fav.attrib[ 'name' ].encode('utf8','ignore')

            favourites[fav_action] = (fav_name, fav_icon, fav_action)

    return favourites

# -------------------------------------------------------------------------------------------------
# Kodi image cache
# -------------------------------------------------------------------------------------------------
# See http://kodi.wiki/view/Caches_explained
# See http://kodi.wiki/view/Artwork
# See http://kodi.wiki/view/HOW-TO:Reduce_disk_space_usage
# See http://forum.kodi.tv/showthread.php?tid=139568 (What are .tbn files for?)
#
# Whenever Kodi downloads images from the internet, or even loads local images saved along
# side your media, it caches these images inside of ~/.kodi/userdata/Thumbnails/. By default,
# large images are scaled down to the default values shown below, but they can be sized
# even smaller to save additional space.

#
# Gets where an image is located in Kodi image cache.
# image_path is a Unicode string.
# cache_file_path is a Unicode string.
#
def kodi_get_cached_image_FN(image_FN):
    FileNameFactory.create
    THUMBS_CACHE_PATH_FN = FileNameFactory.create('special://profile/Thumbnails')
    # >> This function return the cache file base name
    base_name = xbmc.getCacheThumbName(image_FN.getOriginalPath())
    cache_file_path = THUMBS_CACHE_PATH_FN.pjoin(base_name[0]).pjoin(base_name)

    return cache_file_path

#
# Updates Kodi image cache for the image provided in img_path.
# In other words, copies the image img_path into Kodi cache entry.
# Needles to say, only update image cache if image already was on the cache.
# img_path is a Unicode string
#
def kodi_update_image_cache(img_path_FN):
    # What if image is not cached?
    cached_thumb_FN = kodi_get_cached_image_FN(img_path_FN)
    log_debug('kodi_update_image_cache()       img_path_FN OP {0}'.format(img_path_FN.getOriginalPath()))
    log_debug('kodi_update_image_cache()   cached_thumb_FN OP {0}'.format(cached_thumb_FN.getOriginalPath()))

    # For some reason xbmc.getCacheThumbName() returns a filename ending in TBN.
    # However, images in the cache have the original extension. Replace the TBN extension
    # with that of the original image.
    cached_thumb_ext = cached_thumb_FN.getExt()
    if cached_thumb_ext == '.tbn':
        img_path_ext = img_path_FN.getExt()
        cached_thumb_FN = FileNameFactory.create(cached_thumb_FN.getOriginalPath().replace('.tbn', img_path_ext))
        log_debug('kodi_update_image_cache() U cached_thumb_FN OP {0}'.format(cached_thumb_FN.getOriginalPath()))

    # --- Check if file exists in the cache ---
    # xbmc.getCacheThumbName() seems to return a filename even if the local file does not exist!
    if not cached_thumb_FN.isfile():
        log_debug('kodi_update_image_cache() Cached image not found. Doing nothing')
        return

    # --- Copy local image into Kodi image cache ---
    # >> See https://docs.python.org/2/library/sys.html#sys.getfilesystemencoding
    log_debug('kodi_update_image_cache() Image found in cache. Updating Kodi image cache')
    log_debug('kodi_update_image_cache() copying {0}'.format(img_path_FN.getOriginalPath()))
    log_debug('kodi_update_image_cache() into    {0}'.format(cached_thumb_FN.getOriginalPath()))
    # fs_encoding = sys.getfilesystemencoding()
    # log_debug('kodi_update_image_cache() fs_encoding = "{0}"'.format(fs_encoding))
    # encoded_img_path = img_path.encode(fs_encoding, 'ignore')
    # encoded_cached_thumb = cached_thumb.encode(fs_encoding, 'ignore')
    try:
        # shutil.copy2(encoded_img_path, encoded_cached_thumb)
        img_path_FN.copy(cached_thumb_FN)
    except OSError:
        log_kodi_notify_warn('AEL warning', 'Cannot update cached image (OSError)')
        lod_debug('Cannot update cached image (OSError)')

# -------------------------------------------------------------------------------------------------
# Kodi Wizards (by Chrisism)
# -------------------------------------------------------------------------------------------------
#
# The wizarddialog implementations can be used to chain a collection of
# different kodi dialogs and use them to fill a dictionary with user input.
#
# Each wizarddialog accepts a key which will correspond with the key/value combination
# in the dictionary. It will also accept a customFunction (delegate or lambda) which
# will be called after the dialog has been shown. Depending on the type of dialog some
# other arguments might be needed.
# 
# The chaining is implemented by applying the decorator pattern and injecting
# the previous wizarddialog in each new one.
# You can then call the method 'runWizard()' on the last created instance.
# 
# Each wizard has a customFunction which will can be called after executing this 
# specific dialog. It also has a conditionalFunction which can be called before
# executing this dialog which will indicate if this dialog may be shown (True return value).
# 
class WizardDialog():
    __metaclass__ = ABCMeta
    
    def __init__(self, property_key, title, decoratorDialog, customFunction = None, conditionalFunction = None):

        self.title = title
        self.property_key = property_key
        self.decoratorDialog = decoratorDialog
        self.customFunction = customFunction
        self.conditionalFunction = conditionalFunction
        self.cancelled = False

    def runWizard(self, properties):

        if not self.executeDialog(properties):
            log_warning('User stopped wizard')
            return None
        
        return properties

    def executeDialog(self, properties):
        
        if self.decoratorDialog is not None:
            if not self.decoratorDialog.executeDialog(properties):
                return False

        if self.conditionalFunction is not None:
            mayShow = self.conditionalFunction(self.property_key, properties)
            if not mayShow:
                log_debug('Skipping dialog for key: {0}'.format(self.property_key))
                return True

        output = self.show(properties)
        
        if self.cancelled:
            return False

        if self.customFunction is not None:
            output = self.customFunction(output, self.property_key, properties)

        if self.property_key:
            properties[self.property_key] = output
            log_debug('Assigned properties[{0}] value: {1}'.format(self.property_key, output))

        return True
        
    @abstractmethod
    def show(self, properties):
        return True

    def _cancel(self):
        self.cancelled = True

#
# Wizard dialog which accepts a keyboard user input.
# 
class KeyboardWizardDialog(WizardDialog):
    
    def show(self, properties):

        log_debug('Executing keyboard wizard dialog for key: {0}'.format(self.property_key))
        originalText = properties[self.property_key] if self.property_key in properties else ''

        textInput = xbmc.Keyboard(originalText, self.title)
        textInput.doModal()

        if not textInput.isConfirmed(): 
            self._cancel()
            return None

        output = textInput.getText().decode('utf-8')
        return output
  
#
# Wizard dialog which shows a list of options to select from.
# 
class SelectionWizardDialog(WizardDialog):

    def __init__(self, property_key, title, options, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.options = options
        super(SelectionWizardDialog, self).__init__(property_key, title, decoratorDialog, customFunction, conditionalFunction)
       
    def show(self, properties):
        
        log_debug('Executing selection wizard dialog for key: {0}'.format(self.property_key))
        dialog = xbmcgui.Dialog()
        selection = dialog.select(self.title, self.options)

        if selection < 0:
            self._cancel()
            return None
       
        output = self.options[selection]
        return output

  
#
# Wizard dialog which shows a list of options to select from.
# In comparison with the normal SelectionWizardDialog, this version allows a dictionary or key/value
# list as the selectable options. The selected key will be used.
# 
class DictionarySelectionWizardDialog(WizardDialog):

    def __init__(self, property_key, title, options, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.options = options
        super(DictionarySelectionWizardDialog, self).__init__(property_key, title, decoratorDialog, customFunction, conditionalFunction)
       
    def show(self, properties):
        
        log_debug('Executing dict selection wizard dialog for key: {0}'.format(self.property_key))
        dialog = DictionaryDialog()
                
        if callable(self.options):
            self.options = self.options(self.property_key, properties)

        output = dialog.select(self.title, self.options)

        if output is None:
            self._cancel()
            return None
       
        return output
    
#
# Wizard dialog which shows a filebrowser.
# 
class FileBrowseWizardDialog(WizardDialog):
    
    def __init__(self, property_key, title, browseType, filter, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.browseType = browseType
        self.filter = filter
        super(FileBrowseWizardDialog, self).__init__(property_key, title, decoratorDialog, customFunction, conditionalFunction)
       
    def show(self, properties):
        
        log_debug('Executing file browser wizard dialog for key: {0}'.format(self.property_key))
        originalPath = properties[self.property_key] if self.property_key in properties else ''

        if callable(self.filter):
            self.filter = self.filter(self.property_key, properties)
       
        output = xbmcgui.Dialog().browse(self.browseType, self.title, 'files', self.filter, False, False, originalPath).decode('utf-8')

        if not output:
            self._cancel()
            return None
       
        return output

#
# Wizard dialog which shows an input for one of the following types:
#    - xbmcgui.INPUT_ALPHANUM (standard keyboard)
#    - xbmcgui.INPUT_NUMERIC (format: #)
#    - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
#    - xbmcgui.INPUT_TIME (format: HH:MM)
#    - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
#    - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
#
class InputWizardDialog(WizardDialog):
           
    def __init__(self, property_key, title, inputType, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.inputType = inputType
        super(InputWizardDialog, self).__init__(property_key, title, decoratorDialog, customFunction, conditionalFunction)
       
    def show(self, properties):
        
        log_debug('Executing {0} input wizard dialog for key: {1}'.format(self.inputType, self.property_key))
        originalValue = properties[self.property_key] if self.property_key in properties else ''

        output = xbmcgui.Dialog().input(self.title, originalValue, self.inputType)

        if not output:
            self._cancel()
            return None

        return output

#
# Wizard dialog which shows you a message formatted with a value from the dictionary.
#
# Example:
#   dictionary item {'token':'roms'}
#   inputtext: 'I like {} a lot'
#   result message on screen: 'I like roms a lot'
#
# Formatting is optional
#
class FormattedMessageWizardDialog(WizardDialog):

    def __init__(self, property_key, title, text, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.text = text
        super(FormattedMessageWizardDialog, self).__init__(property_key, title, decoratorDialog, customFunction, conditionalFunction)
    
    def show(self, properties):

        log_debug('Executing message wizard dialog for key: {0}'.format(self.property_key))
        format_values = properties[self.property_key] if self.property_key in properties else ''
        full_text = self.text.format(format_values)
        output = xbmcgui.Dialog().ok(self.title, full_text)

        if not output:
            self._cancel()
            return None
        
        return output


#
# Wizard dialog which does nothing or shows anything.
# It only sets a certain property with the predefined value.
# 
class DummyWizardDialog(WizardDialog):

    def __init__(self, property_key, predefinedValue, decoratorDialog, customFunction = None, conditionalFunction = None):
        
        self.predefinedValue = predefinedValue
        super(DummyWizardDialog, self).__init__(property_key, None, decoratorDialog, customFunction, conditionalFunction)

    def show(self, properties):
        
        log_debug('Executing dummy wizard dialog for key: {0}'.format(self.property_key))
        return self.predefinedValue

# 
# Kodi dialog with select box based on a dictionary
# 
class DictionaryDialog(object):
    
    def __init__(self):
        self.dialog = xbmcgui.Dialog()

    def select(self, title, dictOptions):
        
        selection = self.dialog.select(title, dictOptions.values())

        if selection < 0:
            return None

        return dictOptions.keys()[selection]

class ProgressDialogStrategy(object):
    
    def __init__(self):

        self.progress = 0
        self.progressDialog = xbmcgui.DialogProgress()
        self.verbose = True

    def _startProgressPhase(self, title, message):        
        self.progressDialog.create(title, message)

    def _updateProgress(self, progress, message1 = None, message2 = None):
        
        self.progress = progress

        if not self.verbose:
            self.progressDialog.update(progress)
        else:
            self.progressDialog.update(progress, message1, message2)

    def _updateProgressMessage(self, message1, message2 = None):

        if not self.verbose:
            return

        self.progressDialog.update(self.progress, message1, message2)

    def _isProgressCanceled(self):
        return self.progressDialog.iscanceled()

    def _endProgressPhase(self, canceled=False):
        
        if not canceled:
            self.progressDialog.update(100)

        self.progressDialog.close()