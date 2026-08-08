// Print Doctor OctoPrint plugin - tab UI
$(function () {
    function PrintDoctorViewModel(parameters) {
        var self = this;
        self.messages = ko.observableArray([]);

        self.onStartup = function () {
            OctoPrint.socket.onMessage("plugin", function (plugin, data) {
                if (plugin === "print_doctor" && data.type === "defect") {
                    self.messages.unshift({
                        text: data.message,
                        time: new Date(data.time * 1000).toLocaleTimeString()
                    });
                    // keep last 20
                    self.messages(self.messages().slice(0, 20));
                }
            });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PrintDoctorViewModel,
        dependencies: [],
        elements: ["#tab_plugin_print_doctor"]
    });
});
