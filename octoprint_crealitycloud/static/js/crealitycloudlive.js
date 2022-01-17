$(function () {
    function CrealitycloudliveViewModel(parameters) {
        var self = this;
        self.loginState = parameters[0];
        self.dateList = ko.observableArray();
        self.hourList = ko.observableArray();
        self.videoList = ko.observableArray();
        self.markedForFileDeletion = ko.observableArray([]);
        self.recorderStatus = ko.observable("");

        self.isTimelapseViewable = function (data) {
            var url = data.url;
            return (
                self.loginState.hasPermission(
                    self.access.permissions.TIMELAPSE_DOWNLOAD
                ) && url.indexOf(".mp4") >= 0
            );
        };

        self.getStatus = function () {
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: PLUGIN_BASEURL + "crealitycloud/getRecorderStatus",
                data: {},
                dataType: "json",
                success: function (data) {
                    if (data) {
                        self.recorderStatus = data.status;
                    }
                },
            });
        }

        self.recorderAction = function (action) {
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: PLUGIN_BASEURL + "crealitycloud/recorderAction",
                data: {action: action},
                dataType: "json",
                success: function (data) {
                    if (data) {
                        console.log(data)
                        self.getStatus();
                        if (data.code === 5) {
                            alert(data.message)
                        }
                    }
                },
            });
        }

        self.playVideo = function (fileName) {
            var date = $("#date-list").find("option:selected").text();
            var hour = $("#hour-list").find("option:selected").text();
            var videoUrl =
                "/plugin/crealitycloud/" +
                date +
                "/" +
                hour +
                "/" +
                fileName;
            var previewModal = $("#timelapsePreviewModal");
            previewModal
                .children("div.modal-body")
                .children("video")
                .attr("src", videoUrl);
            previewModal
                .off("hidden.bs.modal")
                .on("hidden.bs.modal", function () {
                    $(this).attr("src", "");
                });
            previewModal.modal("show");
        };

        self.getDataList = function () {
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: PLUGIN_BASEURL + "crealitycloud/getVideoDate",
                data: {},
                dataType: "json",
                success: function(data) {
                    if (data) {
                        self.dateList = data.list;
                        self.getHourList(data.list[0]);
                    }
                }
            });
        };

        self.getHourList = function (date) {
            var str = date || $("#date-list").find("option:selected").text();
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: PLUGIN_BASEURL + "crealitycloud/getVideoHour",
                data: { date: str },
                dataType: "json",
                success: function (data) {
                    if (data) {
                        self.hourList.removeAll();
                        data.list.forEach((element) => {
                            self.hourList.push(element);
                        });
                        self.getVideoList(date, data.list[0]);
                    }
                },
            });
        }

        self.getVideoList = function (date, hour) {
            var dataStr = date || $("#date-list").find("option:selected").text();
            var hourStr =
                hour || $("#hour-list").find("option:selected").text();
            $.ajax({
                type: "GET",
                contentType: "application/json; charset=utf-8",
                url: PLUGIN_BASEURL + "crealitycloud/getVideoList",
                data: { date: dataStr, hour: hourStr },
                dataType: "json",
                success: function (data) {
                    if (data) {
                        self.videoList.removeAll();
                        data.list.forEach((element) => {
                            self.videoList.push(element);
                        });
                    }
                },
            });
        }
        self.getStatus();
        self.getDataList();
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: CrealitycloudliveViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: ["loginStateViewModel"],
        // Elements to bind to, e.g. #settings_plugin_crealitycloud, #tab_plugin_crealitycloud, ...
        elements: ["#tab_plugin_crealitycloud"],
    });
});
