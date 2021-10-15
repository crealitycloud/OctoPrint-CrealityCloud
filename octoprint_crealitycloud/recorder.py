from ffmpy import FFmpeg
from ffmpy import FFRuntimeError
import os
import platform
import threading
import time


class Recorder(threading.Thread):
    def __init__(self, thread_id):
        threading.Thread.__init__(self)
        self.mjpg_stream_url = "http://172.23.215.115:8080/?action=stream"
        self.thread_id = thread_id
        self.ffmpeg = None
        self.recorder_file_path = os.path.expanduser('~') + "/" + "creality_recorder"
        if not os.path.isdir(self.recorder_file_path):
            os.mkdir(self.recorder_file_path)

    @staticmethod
    def get_platform(self):
        """
        :return: platform str for ffmpeg
        """
        sys = platform.system()
        if sys == "Windows":
            return "win_x64"
        else:
            return "linux"

    def get_recorder_path_size(self):
        """
        :return: path total size
        """
        if not os.path.exists(self.recorder_file_path):
            return 0
        total_size = 0
        for str_root, ls_dir, ls_files in os.walk(self.recorder_file_path):
            for str_dir in ls_dir:
                total_size = total_size + self.get_recorder_path_size(os.path.join(str_root, str_dir))
            for str_file in ls_files:
                total_size = total_size + os.path.getsize(os.path.join(str_root, str_file))

        return total_size

    def start_recorder(self):
        path = self.recorder_file_path
        if self.get_platform(self) == "win_x64":
            self.ffmpeg = FFmpeg(
                #global_options={"--stdin none --stdout none --stderr none --exit-code 42"},
                inputs={self.mjpg_stream_url: None},
                outputs={path + '/out_%02d.mp4': ["-vf",
                                                  "drawtext=fontfile='C\:/Windows/fonts/Arial.ttf': text='%{pts\:localtime\:" + str(
                                                      time.time()) + "}': x=10: y=10: fontcolor=white: box=1: boxcolor=0x00000000@1",
                                                  "-f", "segment", "-segment_time", "60", "-reset_timestamps", "1",
                                                  "-vcodec", "libx264"]}
            )
        else:
            self.ffmpeg = FFmpeg(
                inputs={self.mjpg_stream_url: None},
                outputs={path + '/out_%02d.mp4': ["-vf",
                                                  "drawtext=fontfile=Arial.ttf: text='%{pts\:localtime\:" + str(
                                                      time.time()) + "}': x=10: y=10: fontcolor=white: box=1: boxcolor=0x00000000@1",
                                                  "-f", "segment", "-segment_time", "60", "-reset_timestamps", "1",
                                                  "-vcodec", "libx264"]}
            )
        try:
            self.ffmpeg.run()
        except FFRuntimeError as ex:
            if ex.exit_code and ex.exit_code != 1:
                raise

    def stop_recorder(self):
        self.ffmpeg.process.terminate()

    def run(self):
        self.start_recorder()

if __name__ == '__main__':

    r = Recorder(1)
    r.start()
    time.sleep(10)
    r.stop_recorder()
    print("abccccccccccccccccccccccccc")

