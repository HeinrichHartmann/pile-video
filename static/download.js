function print(msg) {
    const log = $('#log');
    log.append(msg + "\n");
    log.scrollTop(log[0].scrollHeight);
};

$(() => {
    // TODO: Remove polling transport restriction
    const socket = io();
    socket.on("connect", () => {
        print("connected.");
    });
    socket.on("disconnect", () => {
        print("disconnected.");
    });
    socket.on("message", data => {
        print("> " + data);
    });

    $(document).on("click", "#send", function() {
        var data = {};
        data.url = $("#url").val();
        data.av = $('input[name=av]:checked').val();
        $.ajax({
            method: "POST",
            url: "/download/q",
            data: JSON.stringify(data),
            dataType: "json",
            contentType: "application/json",
            error: (jqXHR, textStatus, errorThrown) => {
                console.log("jqXHR" + jqXHR);
                console.log("jqXHR" + jqXHR.status);
                console.log("textStatus" + textStatus);
                console.log("errorThrown" + errorThrown);
                alert(textStatus + errorThrown);
            },
        });
        $('#message').val('').focus();
        return false;
    });

});
