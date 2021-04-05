function L(x) { console.log(x); };
function gallery_show(pattern) {
  const matches_max = 16;
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
  $("#grid .vid").each(function(i,rec) { rec.style.display = "none"; });
  $("#grid .vid").each(function(index, rec) {
    var text = $(rec).find(".vid-title").text().replace(/\s+/g, ' ').toLowerCase();
    if (pmatch(text)) {
      matches++;
      if(matches > matches_max) { return false; };
      rec.style.display = "block";
      let video = $(rec).find("video");
      video.attr("poster", video.attr("data-poster"));
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
});
