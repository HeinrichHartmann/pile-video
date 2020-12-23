$(function () {
    function print(msg){
        $('#log').prepend(msg + "\n");
    };
    if (window.location.protocol == "https:") {
        ws_url = 'wss://'+window.location.host+'/websocket';
    } else {
        ws_url = 'ws://'+window.location.host+'/websocket';
    }
    ws = new WebSocket(ws_url);
    console.log(ws_url);
    ws.onopen = function(evt) {
        print("> Connection established.");
    };
    ws.onmessage = function(evt) {
        print(evt.data);
    };
    ws.onclose = function(evt) {
        print("> Connection closed.");
    };
    $(document).on("click","#send",function(){
        var data={};
        data.url = $("#url").val();
        data.resolution = $("#selResolution").val();
        $.ajax({
            method : "POST"
            , url : "/youtube-dl/q"
            , data : JSON.stringify(data)
            , dataType : "json"
            , contentType: "application/json"
            , success:function(data,status){
                /* print(data.msg); */
            }
            , error:function (jqXHR, textStatus, errorThrown) {
                console.log("jqXHR"+jqXHR);
                console.log("jqXHR"+jqXHR.status);
                console.log("textStatus"+textStatus);
                console.log("errorThrown"+errorThrown);
                alert(textStatus + errorThrown);
            }
        });
        $('#message').val('').focus();
        return false;

    });

});
