/*
 * View model for OctoPrint-Crealitycloud
 *
 * Author: hemiao & xiongrui
 * License: AGPLv3
 */
$(function () {
  function CrealitycloudViewModel(parameters) {
    var self = this;
    self.isAcitived = ko.observable(false);
    self.activedMsg = ko.observable("");
    self.appdownloadUrl = ko.observable("");
    // assign the injected parameters, e.g.:
    
    // TODO: Implement your plugin's view model here.

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
