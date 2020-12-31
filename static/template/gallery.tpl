<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">
    <link rel="icon" href="../../favicon.ico">
    <title>youtube-dl</title>
    <link href="youtube-dl/static/vendor/bootstrap.min.css" rel="stylesheet">
    <link href="youtube-dl/static/css/gallery-style.css" rel="stylesheet">
    <link href="https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css" rel="stylesheet">
  </head>
  <body>
    <div class="site-wrapper">
      <div class="site-wrapper-inner">
        <div class="cover-container">
          <div class="inner cover">
            <h1 class="cover-heading">Video Gallery</h1>
            <div id="row">
              <div style="width:650px; margin-right:auto; margin-left:auto">
                <form id="form1">
                  <div class="input-group">
                    <input name="url" id="search" type="text" class="form-control" placeholder="Weih..." >
                    <span class="input-group-btn">
                      <button href="#" id ="go" class="btn btn-primary">Go</button>
                    </span>
                  </div>
                </form>
              </div>
              <div class="grid grid-cols-4 gap-4" id="grid">
                % for video in videos:
                <div class="vid" style="display:none">
                  <span class="vid-title">
                    <a href="{{video["src"]}}">{{video["name"]}}</a>
                  </span>
                  <video controls class="player" poster="{{video["src"]}}.png" preload="none">
                    <source src="{{video["src"]}}" type="video/mp4" />
                  </video>
                </div>
                % end
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <script src="youtube-dl/static/vendor/jquery-3.5.1.min.js"></script>
    <script src="youtube-dl/static/vendor/bootstrap.min.js"></script>
    <script src="youtube-dl/static/js/gallery.js"></script>
  </body>
</html>
