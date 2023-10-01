<!DOCTYPE html>
<html lang="en">
    <head>
        <title>Pile Video Gallery</title>
        <link href="/static/vendor/tailwind.min.css" rel="stylesheet">
    </head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
     <body>
        <div id="player" class="hidden block fixed h-full w-full bg-black">
        </div>
        <div id="gallery">
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
                                    <a href="/" class="bg-gray-900 text-white px-3 py-2 rounded-md text-sm font-medium">Gallery</a>
                                    <a href="/download" class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">Downloader</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            <!-- Search bar -->
            <header class="bg-white shadow">
                <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                    <div class="relative text-gray-600 focus-within:text-gray-400">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-2">
                            <button type="submit" class="p-1 focus:outline-none focus:shadow-outline">
                                <svg fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 24 24" class="w-6 h-6">
                                    <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                </svg>
                            </button>
                        </span>
                        <input
                            type="search" name="q" id="search"
                            class="w-full py-2 text-lg text-black bg-gray-100 rounded-md pl-10 focus:outline-none focus:bg-gray-100 focus:text-gray-900"
                            placeholder="Search..." autocomplete="off"
                            autofocus
                        >
                    </div>
                </div>
            </header>

            <!-- Gallery -->
            <main>
               <div id="grid" class="p-4 grid gap-4 lg:grid-cols-4 md:grid-cols-3 sm:grid-cols-2" >
                    {% for video in videos %}
                    <div class="vid hidden flex-col justify-between p-4 bg-gray-200 rounded-lg mb-6 shadow-md"
                         style="display: none;"
                         video-src="{{video["src"]}}"
                         video-poster="{{video["poster"]}}"
                         video-name="{{video["name"]}}"
                    >
                    </div>
                    {% endfor %}
                </div>
            </main>
        </div>

        <!-- Queu -->
        <div id="queuebar" class="bg-white shadow fixed bg-gray-800" style="bottom:0; width:100%; heigth:72px;">
            <div id="queue" class="flex max-w-7xl mx-auto py-2 px-4 sm:px-6 lg:px-8">
                <div class="m-2 p-2 h-10 w-10 flex justify-center"  onclick="play_all()">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="white">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                    </svg>
                </div>
            </div>
        </div>
        <script src="/static/vendor/jquery-3.5.1.min.js"></script>
        <script src="/static/gallery.js"></script>
    </body>
</html>
