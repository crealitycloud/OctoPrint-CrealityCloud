import os

import octoprint
import octoprint.filemanager.analysis
import octoprint.filemanager.storage
import octoprint.plugin
import octoprint.slicing
import octoprint.util
from octoprint.filemanager import FileManager, destinations
from octoprint.filemanager.destinations import FileDestinations
from octoprint.printer.profile import PrinterProfileManager
from octoprint.settings import settings


class filecontrol(object):
    def __init__(self):

        self._fileinfo = ""
        self._filedict = {}
        self._filelist = []
        self._repfilelist = []

        self._settings = settings()

        analysis_queue_factories = {
            "gcode": octoprint.filemanager.analysis.GcodeAnalysisQueue
        }
        analysisQueue = octoprint.filemanager.analysis.AnalysisQueue(
            analysis_queue_factories
        )
        printerProfileManager = PrinterProfileManager()
        slicingManager = octoprint.slicing.SlicingManager(
            self._settings.getBaseFolder("slicingProfiles"), printerProfileManager
        )
        storage_managers = {}
        storage_managers[
            FileDestinations.LOCAL
        ] = octoprint.filemanager.storage.LocalFileStorage(
            self._settings.getBaseFolder("uploads"),
            really_universal=self._settings.getBoolean(
                ["feature", "enforceReallyUniversalFilenames"]
            ),
        )
        self.Filemanager = FileManager(
            analysisQueue,
            slicingManager,
            printerProfileManager,
            initial_storage_managers=storage_managers,
        )

    # 获取树莓派TF卡中的文件信息,储存至self._filelist
    def _getTFfileinfo(self):
        origin = FileDestinations.LOCAL
        path = None
        filter_func = None
        recursive = True
        level = 0
        allow_from_cache = True
        self._filelist = list(
            self.Filemanager.list_files(
                origin,
                path=path,
                filter=filter_func,
                recursive=recursive,
                level=level,
                force_refresh=not allow_from_cache,
            )[origin].values()
        )
        # 按照文件修改时间重新排序
        self._filelist = sorted(self._filelist, key=lambda x: x["date"], reverse=True)

    # 生成符合上报格式的字符串，返回self._filelist列表，其中下标为page（页数）
    def _createfilelist(self):

        # 生成文件信息字典-self._filedict
        num_fileinfo = 0
        page = 0
        self._filedict.clear()
        self._fileinfo = ""
        self._repfilelist = []
        for file in self._filelist:
            # 若当前页已满五条，将self._filedict储存到self._filelist并清空
            if num_fileinfo >= 5:
                self._filedict = {"tf": 0, "fileinfo": self._fileinfo, "pageindex": page}
                self._repfilelist.append(self._filedict)
                page = page + 1
                self._filedict = {}
                self._fileinfo = ""
                num_fileinfo = 0
            # 生成文件信息字符串
            self._fileinfo = (
                str(self._fileinfo)
                + "/local:"
                + str(file["name"])
                + ":"
                + str(file["size"])
                + ":"
                + str(file["date"])
                + ";"
            )
            num_fileinfo = num_fileinfo + 1
        # 将最后一页self._filedict储存到self._filelist
        self._filedict = {"tf": 0, "fileinfo": self._fileinfo, "pageindex": page}
        self._repfilelist.append(self._filedict)

    # 按页数返回文件信息字符串
    def repfile(self, origin, p):
        # 若是重新读取文件
        if p == 0:
            # 来源是TF卡
            if origin == 0:
                self._getTFfileinfo()
                self._createfilelist()
        if p < len(self._repfilelist):
            return self._repfilelist[p]
        else:
            return None

    # 文件的删除与重命名
    def controlfiles(self, v):
        if "delete" in v:
            if "local" in v:
                destination = FileDestinations.LOCAL
                path = str(v).lstrip("deleteprt:/local/")
                self.Filemanager.remove_file(destination, path)
        if "rename" in v:
            if "local" in v:
                v = str(v).lstrip("renameprt:/local:")
                oldname = ""
                newname = ""
                for x in v:
                    if x != ":":
                        newname = newname + x
                    else:
                        oldname = newname
                        newname = ""
                target = FileDestinations.LOCAL
                oldname = self.Filemanager.path_on_disk(target, oldname)
                newname = self.Filemanager.path_on_disk(target, newname)
                try:
                    os.rename(oldname, newname)
                except Exception as e:
                    print(e)
