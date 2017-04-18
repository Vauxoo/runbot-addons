(function($) {
     "use strict";
     function getLog() {
        $.ajax({
            url: _.str.sprintf('/runbot/static/build/%s/logs/job_10_test_base.txt', $(this).data('runbot-build')),
            dataType: 'text',
            success: function(text) {
                $("pre").text(text);
                setTimeout(getLog, 3000); // refresh every 3 seconds
                console.log("logging...");
                console.log("url: " + url);
            },
        });
     }

     getLog();

})(jQuery);
