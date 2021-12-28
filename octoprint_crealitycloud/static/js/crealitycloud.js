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
        $("#bindCrealityCloud").html("Refersh in " + (self.WAIT_TIMEOUT - self.HAS_WAIT_TIMEOUT) + "seconds")
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
