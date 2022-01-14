from re import T
from ffmpy import FFmpeg
from ffmpy import FFRuntimeError
import os
import platform
import threading
import time
import logging
import json
import shutil

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
        self.mjpg_stream_url = "http://127.0.0.1/webcam/?action=stream"
        self.timer = None
        self.ffmpeg = None
        self._logger = logging.getLogger("octoprint.plugins.crealitycloudrecorder")
        self._limit_size = 500 # limit size 500MB
        self._printid = None
        self._recorder_file_path = os.path.expanduser('~') + "/" + "creality_recorder"
        self._recorder_list_path = os.path.expanduser('~') + "/" + "creality_recorder" + "/" + "vlist.json"
        if not os.path.isdir(self._recorder_file_path):
            os.mkdir(self._recorder_file_path)
        self.ffmpeg_play = None
        self.path_play = None
        self.flag = 0

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
        #path = self._recorder_file_path + "/" + time.strftime("%Y-%m-%d", time.localtime()) + "/" + time.strftime("%H",
        #                                                                                                         time.localtime())
        path = self._recorder_file_path + "/" + time.strftime("%Y-%m-%d", time.localtime()) + "/" + str(self._printid)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path

    def get_date_dir_list(self):
        path = self._recorder_file_path
        return os.listdir(path)

    def get_hour_dir_list(self, date):
        path = self._recorder_file_path + "/" + date
        return os.listdir(path)

    def get_min_dir_list(self, date, hour):
        path = self._recorder_file_path + "/" + date + "/" + hour
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
        return total_size
    
    def get_dir_remaining_size(self, path):
        """
        :return int: path remaining size
        """
        st = os.statvfs(path)
        remaining_size = st.f_bavail * st.f_frsize/1024/1024
        return remaining_size

    def set_limit_size(self, size):
        """
        :size int: Recorder limit byte length
        """
        self._limit_size = size

    def is_out_limit_size(self):
        """
        :return bool: Whether the recorder exceeds the limit size
        """
        root_path = os.path.expanduser('~')
        return self.get_dir_remaining_size(root_path) < self._limit_size

    def set_printid(self, printid):
        self._printid = printid

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
                outputs={path + '/%H-%M-%S.mp4': ["-vf",
                                            "drawtext=fontfile='C\:/Windows/fonts/Arial.ttf': text='%{pts\:localtime\:" + str(
                                                time.time()) + "}': x=10: y=10: fontcolor=white: box=1: boxcolor=0x00000000@1",
                                            "-f", "segment", "-strftime", "1", "-segment_time", "60",
                                            "-reset_timestamps", "1",
                                            "-vcodec", "libx264"]}
            )
        else:
            self.ffmpeg = FFmpeg(
                inputs={self.mjpg_stream_url: None},
                outputs={path + '/%H-%M-%S.mp4': ["-vf",
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
        if self.ffmpeg != None:
            self.update_record_time()

        if self.is_out_limit_size():
            self.delete_record_time()

    def run(self):
        """
        Start record and daemon
        """
        if self.ffmpeg == None and self.is_out_limit_size() == False:
            self.timer = RepeatingTimer(1, self.top_of_hour_restart)
            self.timer.start()
            self.add_record_time()
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

    def play(self,path):
        if self.path_play != path:
            self.stop_play()
            self.path_play = path
            t = threading.Thread(target=self.start_play(path))
            t.start()

    def create_record_list(self):
        jsontext = {"cmd":"getRecordList","sn":"1","format":"mp4","playbacks":[]}
        jsondata = json.dumps(jsontext,indent=4,separators=(',', ': '))
        fp = open(self._recorder_list_path, 'w+')
        fp.write(jsondata)
        fp.close()

    def check_record_list(self):
        if os.access(self._recorder_list_path,os.F_OK):
            return
        else: 
            self.create_record_list()

    def add_record_time(self):
        self.check_record_list()
        date = time.strftime("%Y-%m-%d", time.localtime())
        base_dict = {"printId":"NONE","start":"NONE","end":"NONE"}
        base_dict["printId"] = self._printid
        base_dict["start"]= time.strftime("%Y-%m-%d__%H-%M-%S", time.localtime())
        base_dict["end"]= time.strftime("%Y-%m-%d__%H-%M-%S", time.localtime())
        if os.access(self._recorder_list_path,os.F_OK):
            with open(self._recorder_list_path,'r',encoding='utf-8') as load_f:
                load_dict = json.load(load_f)                                   
            with open(self._recorder_list_path,'w',encoding='utf-8') as dump_f:
                load_list = load_dict['playbacks']                              
                for i, date_dict in enumerate(load_list):                       
                    for i in date_dict:  
                        if i == date:                               
                            date_dict[i].append(base_dict)
                            json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': '))  
                            dump_f.close()
                            return
                load_dict['playbacks'].append({date:[base_dict]})
                json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': '))  
                dump_f.close()

    def update_record_time(self):
        printid = self._printid
        if os.access(self._recorder_list_path,os.F_OK):
            with open(self._recorder_list_path,'r',encoding='utf-8') as load_f:
                load_dict = json.load(load_f)                                   
            with open(self._recorder_list_path,'w',encoding='utf-8') as dump_f:
                load_list = load_dict['playbacks']                              
                for i, date_dict in enumerate(load_list):                       
                    for i in date_dict:                                 
                        printid_list = date_dict[i]                             
                        for i, print_dict in enumerate(printid_list):            
                            for i in print_dict:                                
                                if printid == print_dict['printId']:            
                                    print_dict['end'] = time.strftime("%Y-%m-%d__%H-%M-%S", time.localtime())
                                    json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': '))
                                    dump_f.close()
                                    return
                json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': '))
                dump_f.close()
        else:
            self.add_record_time()

    def delete_record_time(self):
        if os.access(self._recorder_list_path,os.F_OK):
            with open(self._recorder_list_path,'r',encoding='utf-8') as load_f:
                load_dict = json.load(load_f)
            with open(self._recorder_list_path,'w',encoding='utf-8') as dump_f:                                   
                load_list = load_dict['playbacks']                              
                for i, date_dict in enumerate(load_list):                       
                    for i in date_dict:       
                        date = i 
                        record_path = self._recorder_file_path + "/" +date
                        if os.path.exists(record_path):
                            del date_dict[i]
                            shutil.rmtree(record_path)
                            json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': ')) 
                            load_f.close()
                            return
                json.dump(load_dict,dump_f,ensure_ascii=False,indent=4,separators=(',', ': ')) 
                load_f.close()

    def start_play(self,path):
        """
        FFmpeg play video
        """        
        outpath = 'rtsp://127.0.0.1:8554/' + path
        if outpath.find('ch0_0') > 0:
            #ffmpeg -i rtsp://172.23.215.16:8086 -loglevel quiet  -b:v 8000K  -tune zerolatency -vcodec h264_omx -preset veryfast -s 320x240 -f rtsp rtsp://172.23.210.218:8554/ch0_0
            #ffmpeg -f mjpeg -r 10 -i http://127.0.0.1/webcam/?action=stream -loglevel quiet -b:v 8000K  -tune zerolatency -vcodec h264_omx -preset veryfast -f rtsp rtsp://127.0.0.1:8554/ch0_0
            self.ffmpeg_play = FFmpeg(
                    #inputs={'rtsp://172.23.215.16:8086': None},
                    inputs={'http://127.0.0.1/webcam/?action=stream': ['-f', 'mjpeg', '-r', '10']},
                    outputs={outpath: ['-q', '0', '-loglevel', 'quiet', '-b:v', '8000K', '-tune', 'zerolatency', '-vcodec', 'h264_omx', '-preset', 'veryfast', '-f', 'rtsp']}
                )
        else:
            listpath = self.create_play_list(path)
            if self.flag ==0:
                outpath = 'rtsp://127.0.0.1:8554/rec-tick-0.h264'
            #ffmpeg  -f concat -i filelist.txt -s 800*480 -b:v 8000K  -tune zerolatency -vcodec h264_omx -preset veryfast -f rtsp rtsp://127.0.0.1:8554/ch0_0
            self.ffmpeg_play = FFmpeg(
                    inputs={listpath: ['-f', 'concat']},
                    outputs={outpath: ['-s', '800*480', '-b:v', '8000K', '-tune', 'zerolatency', '-vcodec', 'h264_omx', '-preset', 'veryfast', '-f', 'rtsp']}
                )
        try:
            self.ffmpeg_play.run()
        except FFRuntimeError as ex:
            self.ffmpeg_play = None
            self.path_play = None
            if ex.exit_code and ex.exit_code != 1:
                self._logger.error(ex)
        time.sleep(1)
        
    def stop_play(self):
        if(self.ffmpeg_play != None):
            self.ffmpeg_play.process.terminate()
            self.ffmpeg_play = None
            self.path_play = None

    def create_play_list(self,path):
        # path表示路径rtsp://127.0.0.1:1172/rec-tick-1637629046.h264
        tsx = 0
        path = path.replace('rec-tick-', '', 1)
        path = path.replace('.h264', '', 1)
        path = time.gmtime(int(path) + 28800)
        datepath = time.strftime("%Y-%m-%d", path)
        path = time.strftime("%Y-%m-%d__%H-%M-%S", path)
        #通过时间戳在vlist.json里找到printid
        if os.access(self._recorder_list_path,os.F_OK):
            with open(self._recorder_list_path,'r',encoding='utf-8') as load_f:
                load_dict = json.load(load_f)                                   
                load_list = load_dict['playbacks']                           
                for i, date_dict in enumerate(load_list):                
                    for i in date_dict:                              
                        printid_list = date_dict[i]                             
                        for i, print_dict in enumerate(printid_list):        
                            for i in print_dict:      
                                ttttt =  print_dict['start']    
                                tsp = int(time.mktime(time.strptime(path, '%Y-%m-%d__%H-%M-%S')))
                                tss = int(time.mktime(time.strptime(print_dict['start'], '%Y-%m-%d__%H-%M-%S')))
                                tse = int(time.mktime(time.strptime(print_dict['end'], '%Y-%m-%d__%H-%M-%S')))              
                                if tss == tsp:            
                                    printidpath = print_dict['printId']
                                    tsx = 0
                                    self.flag = 0
                                elif tss < tsp and tse > tsp:
                                    printidpath = print_dict['printId']
                                    tsx = (tsp -tss)/10
                                    self.flag = 1
                                    
                                    
        filepath = self._recorder_file_path + "/" + datepath + "/" + printidpath
        listpath = filepath + "/" + "playlist.txt"
        # 返回path下所有文件构成的一个list列表
        if os.access(listpath,os.F_OK):    
            os.remove(listpath)     
        filelist=os.listdir(filepath)
        filelist.sort()
        fo = open(listpath, "w")
        i = 0
        for item in filelist:
            if i >= tsx:
                content = "file" + " '" + item + "'\n"          
                fo.write(content)
            else:
                i = i + 1
        fo.close()
        return listpath