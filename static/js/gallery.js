$(() => {
    function L(x) { console.log(x); };
    $("#grid .vid").each(function(index, rec) {
        if (index > 30) { return false; }
        rec.style.display = "block";
    });
    $('#search').keyup(
        (event) => {
            const pattern = event.currentTarget.value.replace(/ +/g, ' ').toLowerCase();
            var matches = 0;
            $("#grid .vid").each(function(index, rec) {
                var text = $(rec).find(".vid-title").text().replace(/\s+/g, ' ').toLowerCase();
                if (!~text.indexOf(pattern)) {
                     rec.style.display = "none";
                } else {
                    matches++;
                    if(matches > 30) { return false; };
                    rec.style.display = "block";
                }
            });
        });
});
