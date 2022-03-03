<!DOCTYPE html>
<html lang="en">
    <head>
        <title>Pile Video</title>
        <link href="/static/vendor/tailwind.min.css" rel="stylesheet">
    </head>
    <body>
        <div>

            <!-- Navbar -->
            <nav class="bg-gray-800">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex items-center justify-between h-16">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <span class="text-3xl font-bold text-gray-100">
                                    Pile Video
                                </span>
                            </div>
                            <div class="hidden md:block">
                                <div class="ml-10 flex items-baseline space-x-4">
                                    <a href="/"
                                       class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Gallery</a>
                                    <a href="/download"
                                       class="bg-gray-900 text-white px-3 py-2 rounded-md text-sm font-medium">Download</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <!-- Search bar -->
            <div class="max-w-5xl mx-auto py-6 px-4 pt-20 h-full">
                <form>
                    <div class="flex">
                        <input id="url" autofocus placeholder="youtube.com/..."
                               class="flex-grow rounded-l-lg p-4 border-t mr-0 border-b border-l text-gray-800 border-gray-200 bg-white"
                        />
                        <button id="send"
                                class="px-8 rounded-r-lg bg-gray-800 text-white font-bold p-4 uppercase border-gary-500 border-t border-b border-r">
                            Download
                        </button>
                    </div>
                    <div class="py-6 flex justify-center">
                        <fieldset id="group1">
                            <input type="radio" value="AV" name="av" checked="checked"> Audio/Video &nbsp;
                            <input type="radio" value="A" name="av"> Audio
                        </fieldset>
                    </div>
                </form>
                <pre id="log"
                     class="text-sm font-mono h-80 rounded border-gray-200 border bg-gray-200 p-5 scroll-y overflow-x-auto"
                ></pre>
            </div>
        </div>

        <script src="/static/vendor/jquery-3.5.1.min.js"></script>
        <script src="/static/vendor/socket.io.min.js"></script>
        <script src="/static/download.js"></script>
    </body>

</html>
