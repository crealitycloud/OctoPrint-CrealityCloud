/*
 * View model for OctoPrint-Crealitycloud
 *
 * Author: hemiao
 * License: AGPLv3
 */
$(function () {
  function CrealitycloudViewModel(parameters) {
    var self = this;
    self.disabled = ko.observable(false);
    self.isAcitived = ko.observable(false);
    self.activedMsg = ko.observable("");
    self.appdownloadUrl = ko.observable("");
    self.WAIT_TIMEOUT = 180;
    self.HAS_WAIT_TIMEOUT = 0;
    // assign the injected parameters, e.g.:
    self.loginStateViewModel = parameters[0];
    self.settingsViewModel = parameters[1];

    //确定btn enable 绑定
    self.allowconfirm = ko.observable(false)
    //下载固件btn enable 绑定
    self.allowdownfw = ko.observable(false)
    //机型选框绑定
    self.selectmodelData = ko.observable(undefined)
    //使用klipper复选框绑定
    self.checkKlipper = ko.observable(false);
    //klipper div隐藏
    self.Klipperable = ko.observable(false)

    // 获取json并绑定机型选框数据
    $.ajax({
      type: "GET",
      contentType: "application/json; charset=utf-8",
      url: PLUGIN_BASEURL + "crealitycloud/getjson",
      data: {},
      dataType: "json",
      success: function (data) {
        self.selectData = ko.observable(data.modellist)
        if (data.klipperable) {
          self.Klipperable = ko.observable(true)
          self.checkKlipper(true)
          self.selectmodelData(data.model)
        }
      }
    })

    //复选框事件
    self.clickKlipper = function () {
      self.Klipperable(self.checkKlipper)
      return true
    }

    //机型选框事件
    self.changemodel = function () {
      if ($("#model").val()) {
        $.ajax({
          type: "GET",
          contentType: "application/json; charset=utf-8",
          url: PLUGIN_BASEURL + "crealitycloud/getjson",
          data: {},
          dataType: "json",
          success: function (data) {
            if (data.model != $("#model").val()) {
              self.allowconfirm(true)
            }
            else {
              self.allowconfirm(false)
            }
          }
        })
      }
      else {
        self.allowconfirm(false)
      }
    }

    //确认按钮事件
    self.clickconfirm = function () {
      if ($("#model").val()) {
        $.ajax({
          type: "POST",
          contentType: "application/json; charset=utf-8",
          url: PLUGIN_BASEURL + "crealitycloud/setmodelid",
          data: JSON.stringify({ id: $("#model").val() }),
          dataType: "json",
          success: function (data) {
            id = $("#model").val()
            if (id >= 0 && id) {
              self.allowdownfw(true)
            }
            else {
              self.allowdownfw(false)
            }
          }
        })
      }
      else {
        self.allowdownfw(false)
      }
    }

    //download firmware
    self.fwdown = function () {
      url = window.location.host;
      $.ajax({
        type: "GET",
        contentType: "application/json; charset=utf-8",
        url: PLUGIN_BASEURL + "crealitycloud/getfwname",
        data: {},
        dataType: "json",
        success: function (data) {
          if (data.fwname != "0") {
            window.open('http://' + url + '/downloads/files/local/' + data.fwname);
          }
        }
      })
    }

    self.qrcode = new QRCode(document.getElementById("qrcode"), {
      text: "",
      width: 128,
      height: 128,
      colorDark: "#000000",
      colorLight: "#ffffff",
      correctLevel: QRCode.CorrectLevel.H
    });
    // TODO: Implement your plugin's view model here.
    self.openCrealityCloud = function () {
      window.open("http://www.crealitycloud.com");
    };
    self.getStatus = function (bInit) {
      $.ajax({
        type: "GET",
        contentType: "application/json; charset=utf-8",
        url: PLUGIN_BASEURL + "crealitycloud/status",
        data: {},
        dataType: "json",
        success: function (data) {
          if (data.actived == 1) {
            self.isAcitived(true);
            self.activedMsg("Machine has actived on " + data.country + " server")
            self.HAS_WAIT_TIMEOUT = self.WAIT_TIMEOUT
          } else {
            self.isAcitived(false);
          }
          if (bInit) {
            if (data.country == "China") {
              self.appdownloadUrl("https://www.crealitycloud.cn")
              $("#region").val("China")
            } else {
              self.appdownloadUrl("https://www.crealitycloud.com")
              $("#region").val("US")
            }

          }
        }
      })
    };

    self.getStatus(true);

    self.waitTimout = function () {
      $.ajax({
        type: "GET",
        contentType: "application/json; charset=utf-8",
        url: PLUGIN_BASEURL + "crealitycloud/machineqr",
        data: {},
        dataType: "json",
        success: function (data) {
          if (data.code != "0") {
            self.makeQR(data.code);
            $("#idCode").html(data.code)

            self.getStatus(false)
          }

        }
      }
      )

      if (self.HAS_WAIT_TIMEOUT < self.WAIT_TIMEOUT) {
        self.HAS_WAIT_TIMEOUT = self.HAS_WAIT_TIMEOUT + 3;
        setTimeout(function () { self.waitTimout(); }, 3000)
        $("#bindCrealityCloud").html("reflush after " + (self.WAIT_TIMEOUT - self.HAS_WAIT_TIMEOUT) + "s")
      } else {
        self.HAS_WAIT_TIMEOUT = 0;
        self.disabled(false);
      }
    }
    self.onReflushQR = function () {
      $.ajax({
        type: "POST",
        contentType: "application/json; charset=utf-8",
        url: PLUGIN_BASEURL + "crealitycloud/makeQR",
        data: JSON.stringify({ country: $("#region").val() }),
        dataType: "json",
        success: function (data) {
          self.HAS_WAIT_TIMEOUT = 0
          //self.disabled(false);
          self.waitTimout()
        }
      }
      )
    }

    self.makeQR = function (code) {
      self.qrcode.clear(); // clear the code.
      self.qrcode.makeCode(code);
    }
    self.bind = function () {
      self.disabled(true);
      self.onReflushQR();
    }
    self.changeRegion = function () {
      let region = $("#region").val();
      if (region == "China") {
        self.appdownloadUrl("https://www.crealitycloud.cn")
      } else {
        self.appdownloadUrl("https://www.crealitycloud.com")
      }
    }
  }

  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: CrealitycloudViewModel,
    // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
    dependencies: ["settingsViewModel", "loginStateViewModel"],
    // Elements to bind to, e.g. #settings_plugin_crealitycloud, #tab_plugin_crealitycloud, ...
    elements: ["#settings_plugin_crealitycloud"]
  });
});
