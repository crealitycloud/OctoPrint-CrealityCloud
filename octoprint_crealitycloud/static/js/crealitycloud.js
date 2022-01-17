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
    // assign the injected parameters, e.g.:
    
    // TODO: Implement your plugin's view model here.

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

    document.getElementById("token_file_input").addEventListener("change",function () {
      console.log("change");
      var selectedFile = document.getElementById('token_file_input').files[0];
      var reader = new FileReader();
      reader.readAsText(selectedFile);
      reader.onload = function(){
        console.log(this.result)
        $.ajax({
          type: "POST",
          contentType: "application/json; charset=utf-8",
          url: PLUGIN_BASEURL + "crealitycloud/get_token",
          data: JSON.stringify({ token: this.result}),
          dataType: "json",
          success: function (data) {
            if (data.code == 0){
              self.isAcitived(true);
              self.getStatus(true)
            }else{
              alert("Fail to install the device due to an invalid file. Please download again or regenerate the Key file.")
            }
          }
        }
        )
      }
    })

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
            self.activedMsg("Raspberry Pi has been activated on the " + data.country + " server")
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
