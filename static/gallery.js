function L(x) {
    console.log(x);
};

function Lajax(jqXHR, textStatus, errorThrown) {
    console.log("jqXHR" + jqXHR);
    console.log("jqXHR" + jqXHR.status);
    console.log("textStatus" + textStatus);
    console.log("errorThrown" + errorThrown);
    alert(textStatus + errorThrown);
};

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
    }
}


function do_queue() {
    $("#queuebar").removeClass("hidden");
    const vid = $(event.target).closest(".vid");
    queue_vid(vid);
}

function queue_vid(vid) {
    const name = vid.attr("video-name");
    const src = vid.attr("video-src");
    const poster = vid.attr("video-poster");
    $("#queue").append($(`
    <div
     video-name="${name}" video-src="${src}"
     class="qitem m-2 p-2 h-10 w-10 bg-gray-100 border-2 rounded border-gray-500 align-middle text-center"
     style="background-image:url('${poster}'); background-size: 200%; background-position: center; background-repeat: no-repeat;"
     onclick="remove_target()"
    ></div>
  `));
}

function remove_target() {
    event.target.remove();
}

function queue_first() {
    const gallery_videos = $("#grid .vid:visible");
    if (gallery_videos.length > 0) {
        queue_vid($(gallery_videos[0]));
    }
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

    // Track views
    $.ajax({
        method: "POST",
        url: "/count",
        data: JSON.stringify({ video: name }),
        dataType: "json",
        contentType: "application/json",
        error: Lajax,
    });
}

function do_play() {
    const rec = $(event.target).closest(".vid");
    const src = rec.attr("video-src");
    player_show();
    const video = player_play(src);
    video.on("ended", player_black);
}

function gallery_show(pattern) {
    const matches_max = 12;
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
        var views = rec.getAttribute("video-views");
        var poster = rec.getAttribute("video-poster");
        if (pmatch(text)) {
            matches++;
            if (matches > matches_max) {
                return false;
            };
            rec.style.display = "flex";
            rec.innerHTML = `
               <div>
                   <div class="preview">
                     <img src="${poster}" class="w-full" onclick="do_queue()">
                     <div class="py-2 pt-4 text-gray-900">
                         <p>${name} (${views})</p>
                     </div>
                   </div>
               </div>
               <div>
                   <button class="my-1 w-full border-2 rounded border-gray-500 hover:bg-green-200" onclick="do_play()">Play</button>
                   <button class="my-1 w-full border-2 rounded border-gray-500 hover:bg-blue-200" onclick="do_queue()">Queue</button>
                   <button class="my-1 w-full border-2 rounded border-gray-500 hover:bg-red-200" onclick="do_delete()">Delete</button>
               </div>
            `;
        }
        return 0;
    });
}

$(() => {
    // Initialize
    gallery_show($('#search').val());
    // Listen to change events
    $('#search').keyup((event) => {
        const pattern = event.currentTarget.value.replace(/ +/g, ' ').toLowerCase();
        gallery_show(pattern);
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
});
