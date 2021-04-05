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
    <link href="youtube-dl/static/css/style.css" rel="stylesheet">
</head>

<body>
<div class="site-wrapper">
    <div class="site-wrapper-inner">
        <div class="cover-container">
            <div class="inner cover">
                <h1 class="cover-heading">youtube-dl</h1>
                <p class="lead">Download files with <a href="https://github.com/ytdl-org/youtube-dl">youtube-dl</a>.</p>
                <p><a href="/gallery">GALLERY</a></p>
                <div class="row">
                    <form id="form1">
                        <div class="input-group">
                            <input name="url" id="url" type="url" class="form-control" placeholder="URL" >
                            <span class="input-group-btn">
                                <button href="#" id ="send" class="btn btn-primary" >
                                  <span class="glyphicon glyphicon-share-alt"  aria-hidden="true"></span> Submit
                                </button>
                            </span>
                        </div>
                        <center>
                        <fieldset id="group1">
                            <input type="radio" value="AV" name="av" checked="checked"> Audio/Video &nbsp;
                            <input type="radio" value="A" name="av"> Audio
                        </fieldset>
                        </center>
                    </form>
                </div>
            </div>
            <hr/>
            <pre id="log"></pre>
        </div>
    </div>
</div>
<script src="youtube-dl/static/vendor/jquery.min.js"></script>
<script src="youtube-dl/static/vendor/bootstrap.min.js"></script>
<script src="youtube-dl/static/logical_js/logic.js"></script>
</body>

</html>
