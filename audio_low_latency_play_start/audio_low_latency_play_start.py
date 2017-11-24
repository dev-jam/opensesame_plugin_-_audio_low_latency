#-*- coding:utf-8 -*-

"""
22-10-2017
Author: Bob Rosbag
Version: 2017.11-1

This file is part of OpenSesame.

OpenSesame is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenSesame is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenSesame.  If not, see <http://www.gnu.org/licenses/>.
"""

#import warnings

from libopensesame.py3compat import *
from libopensesame import debug
from libopensesame.item import item
from libqtopensesame.items.qtautoplugin import qtautoplugin
from libopensesame.exceptions import osexception
from openexp.keyboard import keyboard
import threading
import wave


VERSION = u'2017.11-1'

class audio_low_latency_play_start(item):

    """
    Class handles the basic functionality of the item.
    It does not deal with GUI stuff.
    """

    # Provide an informative description for your plug-in.
    description = u'Low Latency Audio: starts audio playback in the background.'

    def __init__(self, name, experiment, string=None):

        item.__init__(self, name, experiment, string)
        self.verbose = u'no'
        self.poll_time = 1


    def reset(self):

        """Resets plug-in to initial values."""

        # Set default experimental variables and values
        self.var.filename = u''
        self.var.duration = u'sound'
        self.var.delay = 0
        self.var.ram_cache = u'yes'


    def init_var(self):

        """Set en check variables."""

        if hasattr(self.experiment, "audio_low_latency_play_dummy_mode"):
            self.dummy_mode = self.experiment.audio_low_latency_play_dummy_mode
            self.verbose = self.experiment.audio_low_latency_play_verbose
            if self.dummy_mode == u'no':
                self.module = self.experiment.audio_low_latency_play_module
                self.device = self.experiment.audio_low_latency_play_device
                self.audio_buffer = self.experiment.audio_low_latency_play_buffer
                self.data_size = self.experiment.audio_low_latency_play_data_size
                self.bitdepth = self.experiment.audio_low_latency_play_bitdepth
                self.samplerate = self.experiment.audio_low_latency_play_samplerate
                self.channels = self.experiment.audio_low_latency_play_channels
        else:
            raise osexception(
                    u'Audio Low Latency Play Init item is missing')

        self.filename = self.experiment.pool[self.var.filename]
        self.ram_cache = self.var.ram_cache

        self.experiment.audio_low_latency_play_continue = 1
        self.experiment.audio_low_latency_play_start = 1


    def prepare(self):

        """Preparation phase"""

        # Call the parent constructor.
        item.prepare(self)

        # create keyboard object
        self.kb = keyboard(self.experiment,timeout=1)

        self.init_var()

        if self.dummy_mode == u'no':
            try:
                self.show_message(u'\n')
                self.show_message(u'Loading sound file: '+self.filename+' ...')
                self.wav_file = wave.open(self.filename, 'rb')
                self.show_message(u'Succesfully loaded sound file...')
            except Exception as e:
                raise osexception(
                    u'Could not load audio file', exception=e)

            if self.wav_file.getsampwidth() * 8 != self.bitdepth:
                raise osexception(u'wave file has incorrect bitdepth')
            if self.wav_file.getframerate() != self.samplerate:
                raise osexception(u'wave file has incorrect samplerate')
            if self.wav_file.getnchannels() != self.channels:
                raise osexception(u'wave file has incorrect number of channels')

            if self.ram_cache == u'yes':
                wav_file_nframes = self.wav_file.getnframes()
                self.wav_file_data = self.wav_file.readframes(wav_file_nframes)
                self.wav_file.close()


    def run(self):

        """Run phase"""

        self.set_item_onset()
        start_time = self.clock.time()

        if not (hasattr(self.experiment, "audio_low_latency_play_stop") or hasattr(self.experiment, "audio_low_latency_play_wait")):
            raise osexception(
                    u'Audio Low Latency Play Stop or Audio Low Latency Play Wait item is missing')

        error_msg = u'Duration must be a string named sound or a an integer greater than 1'

        if isinstance(self.var.duration,str):
            if self.var.duration == u'sound':
                self.duration_check = False
                self.duration = self.var.duration
            else:
                raise osexception(error_msg)
        elif isinstance(self.var.duration,int):
            if self.var.duration >= 1:
                self.duration_check = True
                self.duration = int(self.var.duration)
            else:
                raise osexception(error_msg)
        else:
            raise osexception(error_msg)

        if isinstance(self.var.delay,int):
            if self.var.delay >= 0:
                self.delay = int(self.var.delay)
                if self.delay > 0:
                    self.delay_check = True
                else:
                    self.delay_check = False
            else:
                raise osexception(u'Delay can not be negative')
        else:
            raise osexception(u'Delay should be a integer')

        if self.dummy_mode == u'no':
            while self.experiment.audio_low_latency_play_locked:
                self.clock.sleep(self.poll_time)

            if self.delay_check:
                time_passed = self.clock.time() - start_time
                delay = self.delay - time_passed
            else:
                delay = self.delay


            self.show_message(u'Starting audio')
            self.experiment.audio_low_latency_play_locked = 1

            if self.ram_cache == u'no':
                self.experiment.audio_low_latency_play_thread = threading.Thread(target=self.play_file, args=(self.device, self.wav_file, self.audio_buffer, delay))
            elif self.ram_cache == u'yes':
                self.experiment.audio_low_latency_play_thread = threading.Thread(target=self.play_data, args=(self.device, self.wav_file_data, self.data_size, delay))

            self.experiment.audio_low_latency_play_thread.start()

        elif self.dummy_mode == u'yes':
            self.show_message(u'Dummy mode enabled, NOT playing audio')
        else:
            raise osexception(u'Error with dummy mode!')


    def play_file(self, stream, wav_file, chunk, delay):

        self.experiment.audio_low_latency_play_thread_running = 1

        data = wav_file.readframes(chunk)

        if self.delay_check:
            if delay >= 1:
                self.clock.sleep(delay)

        self.set_stimulus_onset()
        start_time = self.clock.time()

        while len(data) > 0:
            # Read data from stdin
            stream.write(data)
            data = wav_file.readframes(chunk)

            if self.experiment.audio_low_latency_play_continue == 0:
                break
            elif self.duration_check:
                if self.clock.time() - start_time >= self.duration:
                    break

#        if self.module == self.experiment.pyaudio_module_name:
#            stream.stop_stream()  # stop stream

        wav_file.close()

        self.show_message(u'Stopped audio')
        self.experiment.audio_low_latency_play_locked = 0


    def play_data(self, stream, wav_data, chunk, delay):

        self.experiment.audio_low_latency_play_thread_running = 1

        if self.delay_check:
            if delay >= 1:
                self.clock.sleep(delay)

        self.set_stimulus_onset()
        start_time = self.clock.time()

        if self.module == self.experiment.pyaudio_module_name:
            stream.start_stream()  # stop stream

        for start in range(0,len(wav_data),chunk):
            stream.write(wav_data[start:start+chunk])

            if self.experiment.audio_low_latency_play_continue == 0:
                break
            elif self.duration_check:
                if self.clock.time() - start_time >= self.duration:
                    break

        if self.module == self.experiment.pyaudio_module_name:
            stream.stop_stream()  # stop stream

        self.show_message(u'Stopped audio')
        self.experiment.audio_low_latency_play_locked = 0


    def show_message(self, message):
        """
        desc:
            Show message.
        """

        debug.msg(message)
        if self.verbose == u'yes':
            print(message)


    def set_stimulus_onset(self, time=None):

        """
        desc:
            Set a timestamp for the onset time of the item's execution.

        keywords:
            time:    A timestamp or None to use the current time.

        returns:
            desc:    A timestamp.
        """

        if time is None:
            time = self.clock.time()
        self.experiment.var.set(u'time_%s_stimulus_onset' % self.name, time)
        return time


class qtaudio_low_latency_play_start(audio_low_latency_play_start, qtautoplugin):

    def __init__(self, name, experiment, script=None):

        """plug-in GUI"""

        audio_low_latency_play_start.__init__(self, name, experiment, script)
        qtautoplugin.__init__(self, __file__)
        self.text_version.setText(
        u'<small>Audio Low Latency version %s</small>' % VERSION)
