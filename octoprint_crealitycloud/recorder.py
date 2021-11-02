from re import T
from ffmpy import FFmpeg
from ffmpy import FFRuntimeError
import os
import platform
import threading
import time
import logging


class RecorderOutOfSizeLimitError(Exception):
    def __init__(self, msg):
        self.message = msg
        log = logging.getLogger("octoprint.plugins.crealitycloudrecorder")
        log.info(self.message)
    def __str__(self):
        return self.message


class RepeatingTimer(threading.Timer):
    def run(self):
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


class Recorder(object):
    def __init__(self):
        self.mjpg_stream_url = "http://127.0.0.1:8081/video.mjpg"
        self.timer = None
        self.ffmpeg = None
        self._logger = logging.getLogger("octoprint.plugins.crealitycloudrecorder")
        self._limit_size = 100 * 1024 * 1024 # limit size 100M
        self.recorder_file_path = os.path.expanduser('~') + "/" + "creality_recorder"
        if not os.path.isdir(self.recorder_file_path):
            os.mkdir(self.recorder_file_path)

    @staticmethod
    def get_platform(self):
        """
        :return str: platform str for ffmpeg
        """
        sys = platform.system()
        if sys == "Windows":
            return "win_x64"
        else:
            return "linux"

    def get_new_recorder_hour_dir(self):
        """
        :return str: Recorder hour dir, example '~/creality_recorder/2021-10-28/11'
        """
        path = self.recorder_file_path + "/" + time.strftime("%Y-%m-%d", time.localtime()) + "/" + time.strftime("%H",
                                                                                                                 time.localtime())
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_date_dir_list(self):
        path = self.recorder_file_path
        return os.listdir(path)

    def get_hour_dir_list(self, date):
        path = self.recorder_file_path + "/" + date
        return os.listdir(path)

    def get_min_dir_list(self, date, hour):
        path = self.recorder_file_path + "/" + date + "/" + hour
        return os.listdir(path)

    def get_dir_size(self, path):
        """
        :return int: path total size
        """
        if not os.path.exists(path):
            return 0
        total_size = 0
        for file in os.listdir(path):
            new_dir = os.path.join(path, file)
            if os.path.isdir(new_dir):
                total_size += self.get_dir_size(new_dir)
            elif os.path.isfile(new_dir):
                total_size += os.path.getsize(new_dir)
        # for str_root, ls_dir, ls_files in os.walk(path):
        #     for str_dir in ls_dir:
        #         total_size = total_size + self.get_dir_size(os.path.join(str_root, str_dir))
        #     for str_file in ls_files:
        #         total_size = total_size + os.path.getsize(os.path.join(str_root, str_file))

        return total_size

    def set_limit_size(self, size):
        """
        :size int: Recorder limit byte length
        """
        self._limit_size = size

    def is_out_limit_size(self):
        """
        :return bool: Whether the recorder exceeds the limit size
        """
        return self.get_dir_size(self.recorder_file_path) > self._limit_size

    def start_recorder(self):
        """
        FFmpeg records video and generates a file per minute
        """
        if self.is_out_limit_size():
            raise RecorderOutOfSizeLimitError("Recorder out of size limit")
        path = self.get_new_recorder_hour_dir()
        if self.get_platform(self) == "win_x64":
            self.ffmpeg = FFmpeg(
                inputs={self.mjpg_stream_url: None},
                outputs={path + '/%M.mp4': ["-vf",
                                            "drawtext=fontfile='C\:/Windows/fonts/Arial.ttf': text='%{pts\:localtime\:" + str(
                                                time.time()) + "}': x=10: y=10: fontcolor=white: box=1: boxcolor=0x00000000@1",
                                            "-f", "segment", "-strftime", "1", "-segment_time", "60",
                                            "-reset_timestamps", "1",
                                            "-vcodec", "libx264"]}
            )
        else:
            self.ffmpeg = FFmpeg(
                inputs={self.mjpg_stream_url: None},
                outputs={path + '/%M.mp4': ["-vf",
                                            "drawtext=fontfile=Arial.ttf: text='%{pts\:localtime\:" + str(
                                                time.time()) + "}': x=10: y=10: fontcolor=white: box=1: boxcolor=0x00000000@1",
                                            "-f", "segment", "-strftime", "1", "-segment_time", "60",
                                            "-reset_timestamps", "1",
                                            "-vcodec", "libx264"]}
            )
        try:
            self.ffmpeg.run()
        except FFRuntimeError as ex:
            if ex.exit_code and ex.exit_code != 1:
                self._logger.error(ex)

    def stop_recorder(self):
        """
        Stop FFmpeg by terminating the process
        """
        if(self.ffmpeg == None):
            return
        self.ffmpeg.process.terminate()
        self.ffmpeg = None

    def top_of_hour_restart(self):
        """
        Daemon thread, detects every second whether the process is stopped and
         whether the logger is out of size and restarted on the hour
        """
        if self.ffmpeg == None and self.is_out_limit_size() == False:
            threading.Thread(target=self.start_recorder).start()
        if self.is_out_limit_size():
            self.stop()

        if int(time.time()) % 3600 == 0:
            # Restart the hour
            self.stop_recorder()
            if self.is_out_limit_size():
                self.stop()
            else:
                threading.Thread(target=self.start_recorder).start()

    def run(self):
        """
        Start record and daemon
        """
        if self.ffmpeg == None and self.is_out_limit_size() == False:
            self.timer = RepeatingTimer(1, self.top_of_hour_restart)
            self.timer.start()
        if self.timer != None:
            return True
        else:
            return False

    def stop(self):
        """
        Stop record and daemon
        """
        try:
            self.timer.cancel()
        except Exception as e:
            self._logger.error(e)
        self.timer = None
        self.stop_recorder()
        if self.ffmpeg == None and self.timer == None:
            return True
        else:
            return False

