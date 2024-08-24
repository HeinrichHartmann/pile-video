function L(x) {
    console.log(x);
};

function Lajax(jqXHR, textStatus, errorThrown) {
    console.log("jqXHR: " + jqXHR);
    console.log("jqXHR: " + jqXHR.status);
    console.log("textStatus: " + textStatus);
    console.log("errorThrown: " + errorThrown);
    console.log(arguments.callee.caller.toString());
    alert(textStatus + errorThrown);
};

function isMobile() { return ('ontouchstart' in document.documentElement); }

function duration_to_str(duration) {
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const seconds = Math.floor(duration % 60);
    if (hours > 0) {
        return `${hours}h ${minutes}m ${seconds}s`;
    }
    if (minutes > 0) {
        return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
}

function update_queue_duration() {
    const items = $("#queue .qitem");
    let duration = 0;
    items.each((i, item) => {
        duration += parseInt(item.getAttribute("video-duration"));
    });
    if (duration > 0) {
        $("#queue_duration").text(duration_to_str(duration));
    } else {
        $("#queue_duration").text("");
    }
}

function do_delete() {
    const rec = $(event.target).closest(".vid");
    const src = rec.attr("video-src");
    const name = rec.attr("video-name");
    if (confirm(`Really delete ${name}?`)) {
        $.ajax({
            method: "POST",
            url: "/delete",
            data: JSON.stringify({
                src: src
            }),
            dataType: "json",
            contentType: "application/json",
            error: Lajax,
        });
        rec.remove();
    }
}

function do_queue(event) {
    $("#queuebar").removeClass("hidden");
    const vid = $(event.target).closest(".vid");
    queue_vid(vid);
}

function queue_vid(vid) {
    const name = vid.attr("video-name");
    const src = vid.attr("video-src");
    const poster = vid.attr("video-poster");
    const duration = vid.attr("video-duration");
    $("#queue").append($(`
    <div
     video-name="${name}" video-src="${src}" video-duration="${duration}"
     class="qitem m-2 p-2 h-10 w-10 bg-gray-100 border-2 rounded border-gray-500 align-middle text-center"
     style="background-image:url('${poster}'); background-size: 200%; background-position: center; background-repeat: no-repeat;"
     onclick="remove_target()"
    ></div>
    `));
    update_queue_duration();
}

function remove_target() {
    event.target.remove();
    update_queue_duration();
}

function queue_first() {
    const gallery_videos = $("#grid .vid:visible");
    if (gallery_videos.length > 0) {
        queue_vid($(gallery_videos[0]));
    }
    update_queue_duration();
}

function queue_peek() {
    const items = $("#queue .qitem");
    if (items.length == 0) {
        return null;
    }
    const i = items[0];
    return {
        src: i.getAttribute("video-src"),
        name: i.getAttribute("video-name"),
    };
}

function queue_remove() {
    const items = $("#queue .qitem");
    if (items.length == 0) {
        return;
    }
    const i = items[0];
    i.remove();
    update_queue_duration();
}

function player_close() {
    $("#player video").remove();
    $("#player").addClass("hidden");
    $("#gallery").removeClass("hidden");
}

function player_black() {
    $("#player video")[0].remove();
}

function player_show() {
    $("#player").removeClass("hidden");
    $("#gallery").addClass("hidden");
}

function player_play(src) {
    /* We ran into problems when only changing the src of the source:
       'DOMException: The fetching process for the media resource was aborted by the user agent at the user's request.'
       To avoid this, we replace the whole video element.
     */
    $("#player video").remove();
    const new_video = $(`
      <video controls preload="none" class="w-full" style="height:calc(100% - 72px);">
        <source src ="${src}" type="video/mp4"/>
      </video>
    `);
    $("#player").append(new_video);
    let video = new_video[0];
    video.load();
    video.play().catch((e) => { L(e); });
    return $(video);
}

function play_next() {
    // Avoid recursion by going through the event loop
    setTimeout(play_all, 0);
}

function play_all() {
    entry = queue_peek();
    if (entry == null) {
        player_black();
        return;
    }
    const src = entry['src'];
    const name = entry['name'];
    player_show();
    const video = player_play(src);
    video.on("ended", () => {
        queue_remove();
        play_next();
    });
}

function do_play(event) {
    const rec = $(event.target).closest(".vid");
    const src = rec.attr("video-src");
    player_show();
    const video = player_play(src);
    video.on("ended", player_black);
}

function do_click(event) {
    switch (event.detail) {
        case 1:
            do_queue(event);
            break;
        case 2:
            // double click
            queue_remove();
            do_play(event);
            break;
    }
}


function gallery_show(pattern, matches_max) {
    var matches = 0;
    const fragments = pattern.split(/[ ]+/);

    function pmatch(text) {
        return fragments.every((pat) => {
            if (!~text.indexOf(pat)) {
                return false;
            } else {
                return true;
            }
        });
    }
    $("#grid .vid").each(function(i, rec) {
        rec.style.display = "none";
    });
    $("#grid .vid").empty();
    $("#grid .vid").each(function(index, rec) {
        var text = rec.getAttribute("video-name").replace(/\s+/g, ' ').toLowerCase();
        var name = rec.getAttribute("video-name").replace(/[_ ]+/g, ' ');
        var src = rec.getAttribute("video-src");
        var poster = rec.getAttribute("video-poster");
        var duration = rec.getAttribute("video-duration");
        var duration_str = duration_to_str(duration);
        if (pmatch(text)) {
            matches++;
            if (matches > matches_max) {
                return false;
            };
            rec.style.display = "flex";
            rec.innerHTML = `
               <div>
                   <div class="preview">
                     <img src="${poster}" class="w-full" onclick="do_click(event)">
                     <div class="py-2 pt-4 text-gray-900">
                         <p>${name} (${duration_str})</p>
                     </div>
                   </div>
               </div>
               <div>
                   <button class="my-1 w-full border-2 rounded border-gray-500 hover:bg-red-200" onclick="do_delete(event)">Delete</button>
               </div>
            `;
        }
        return 0;
    });
}

$(() => {
    // Initialize
    var matches_max = 12;
    var pattern = $('#search').val();
    gallery_show(pattern, matches_max);

    // Listen to change events
    $('#search').keyup((event) => {
        pattern = event.currentTarget.value.replace(/ +/g, ' ').toLowerCase();
        matches_max = 12;
        gallery_show(pattern, matches_max);
    });
    $(document).on('keyup.player', (e) => {
        if (e.key === "Escape") {
            return player_close();
        }
        if (e.key === "Enter") {
            return queue_first();
        }
        return null;
    });
    window.onscroll = function(ev) {
        if ((window.innerHeight + window.scrollY) >= 0.95 * document.body.offsetHeight) {
            matches_max += 10;
            gallery_show(pattern, matches_max);
        }
    };

    if (!isMobile()) {
        $('#search').focus();
    }
});
