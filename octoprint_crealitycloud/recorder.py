from ffmpy import FFmpeg
from ffmpy import FFRuntimeError
import os
from subprocess import TimeoutExpired
import platform
import threading
import time
import logging


class RecorderOutOfSizeLimitError(Exception):
    pass


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
        self._limit_size = 100 * 1024 * 1024
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

    def get_dir_size(self, path):
        """
        :return int: path total size
        """
        if not os.path.exists(path):
            return 0
        total_size = 0
        for str_root, ls_dir, ls_files in os.walk(path):
            for str_dir in ls_dir:
                total_size = total_size + self.get_dir_size(os.path.join(str_root, str_dir))
            for str_file in ls_files:
                total_size = total_size + os.path.getsize(os.path.join(str_root, str_file))

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

        if self.is_out_limit_size():
            raise RecorderOutOfSizeLimitError("Recorder out of size limit")
        path = self.get_new_recorder_hour_dir()
        if self.get_platform(self) == "win_x64":
            self.ffmpeg = FFmpeg(
                # global_options={"--stdin none --stdout none --stderr none --exit-code 42"},
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
        self.ffmpeg.process.terminate()
        self.ffmpeg = None

    def top_of_hour_restart(self):
        if self.ffmpeg is None:
            threading.Thread(target=self.start_recorder).start()
        if int(time.time()) % 3600 == 0:
            # Restart the hour
            self.stop_recorder()
            threading.Thread(target=self.start_recorder).start()

    def run(self):
        self.timer = RepeatingTimer(1, self.top_of_hour_restart)

    def stop(self):
        self.timer.cancel()
        self.stop_recorder()


if __name__ == '__main__':
    r = Recorder(1)
    r.run()
    # time.sleep(10)
    # r.stop_recorder()
    # print("abccccccccccccccccccccccccc")
