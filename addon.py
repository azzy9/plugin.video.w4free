import re
import json
import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import six

from six.moves import urllib, urllib_parse
from StorageServer import StorageServer

WEB_URL = "https://w4free.com"
media_types = ["series_1", "movies", "sport"]
media_names = ["Series", "Movies", "Sports"]
media_mode = ["episodes", "play", "episodes"]

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
addon = xbmcaddon.Addon()
args = urllib_parse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(addon_handle, "movies")

PLUGIN_ID = base_url.replace("plugin://","")
MEDIA_URL = 'special://home/addons/{0}/resources/media/'.format(PLUGIN_ID)

def fetchURL( url ):
    html = urllib.request.urlopen( url )
    if html.getcode() != 200:
        raise

    return html.read()

def construct_request(query):
    return base_url + "?" + urllib_parse.urlencode(query)

xbmc.log(sys.argv[2], xbmc.LOGWARNING)
mode = args.get("mode", None)
if mode is not None:
    mode = mode[0]

if mode is None:

    # Type selection
    for i, variant in enumerate(media_types):
        list_item = xbmcgui.ListItem(media_names[i])
        list_item.setArt({
            "icon":MEDIA_URL + media_names[i] + '.jpg',
            "poster":MEDIA_URL + media_names[i] + '.jpg',
        });
        callback = construct_request({
            "mode": "channels",
            "type": variant,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle,
            url = callback,
            listitem = list_item,
            isFolder = True
        )
    xbmcplugin.endOfDirectory(addon_handle)

elif mode == "channels":

    variant = args.get("type", [""])[0]

    html = fetchURL(WEB_URL + "/" + variant)
    dataStartIndex = html.find(b'class="collections"')
    
    if dataStartIndex == -1:
        raise Exception(r'list scrape fail: ' + variant)

    result = re.finditer(
        b'''href=\"([^\"]*)\">\s*<div\s*class=\"cover\"\s*style=\"background:url\(([^\)]*)\)\s*no-repeat;''',
        html[dataStartIndex : html.find(b'<footer')]
    )

    for match in result:
        title = match.groups()[0].decode('utf-8').replace('&amp;','&').replace('/','').replace('-',' ');
        list_item = xbmcgui.ListItem( title )
        for art_type in ["thumb", "poster", "banner", "fanart","icon"]:
            list_item.setArt({art_type:match.groups()[1]})
        callback = construct_request({
            "url": match.groups()[0],
            "mode": media_mode[ media_types.index(variant) ],
            "title": title,
            "thumb": match.groups()[1],
            "isdirect": False,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle,
            url = callback,
            listitem = list_item,
            isFolder = True
        )
    xbmcplugin.endOfDirectory(addon_handle)

elif mode == "episodes":

    variant = args.get("url", [""])[0]
    title = args.get("title", [""])[0]
    thumb = args.get("thumb", [""])[0]

    html = fetchURL(WEB_URL + variant)
    dataStartIndex = html.find(b'episode_dropdown')
    
    if dataStartIndex == -1:
        raise Exception(r'list scrape fail: ' + variant)

    result = re.finditer(
        b'''<li class=\"([^\"\']+)\"\s*>\s*<A href=\"([^\"\']+)\">([^\"\']+)</A>''',
        html[dataStartIndex : html.find(b'id="body"')]
    )

    for match in result:

        direct = False
        cclass = match.groups()[0].decode('utf-8')
        rurl = match.groups()[1].decode('utf-8')
        title = match.groups()[2].decode('utf-8').strip().replace('&amp;','&');
        list_item = xbmcgui.ListItem( title )

        for art_type in ["thumb", "poster", "banner", "fanart","icon"]:
            list_item.setArt({art_type:thumb})

        #no point scraping to get the url again since we can already get it
        if r"active" in cclass:
            dataStartIndex = html.find(b'class="logo"')
            #xbmc.log(html.decode('utf-8'), xbmc.LOGWARNING)
            if dataStartIndex == -1:
                raise Exception(r'list scrape fail: ' + variant)
            rurl = re.findall(b'''<source\s*src=\"([^\"]+\.mp4)\"''', html[dataStartIndex : html.find(b'<footer')])[0]
            direct = True

        if isinstance( rurl, bytes ):
            rurl.decode('utf-8')

        callback = construct_request({
            "url": rurl,
            "mode": "play",
            "title": title,
            "thumb": thumb,
            "isdirect": direct,
        })
        xbmcplugin.addDirectoryItem(
            handle = addon_handle,
            url = callback,
            listitem = list_item,
            isFolder = True
        )
    xbmcplugin.endOfDirectory(addon_handle)

elif mode == "play":

    variant = args.get("url", [""])[0]
    title = args.get("title", [""])[0]
    thumb = args.get("thumb", [""])[0]
    direct = ( args.get("isdirect", [""])[0] == "True" )

    if direct:
        source = variant
    else:
        xbmc.log(WEB_URL + variant, xbmc.LOGWARNING)
        html = fetchURL(WEB_URL + variant)
        dataStartIndex = html.find(b'class="logo"')
        #xbmc.log(html.decode('utf-8'), xbmc.LOGWARNING)
        if dataStartIndex == -1:
            raise Exception(r'list scrape fail: ' + variant)

        source = re.findall(b'''<source\s*src=\"([^\"]+\.mp4)\"''', html[dataStartIndex : html.find(b'<footer')])[0]

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    list_item = xbmcgui.ListItem(source)
    list_item.setInfo( type="Video", infoLabels={ "Title": title } )
    list_item.setArt({"thumb":thumb})

    playlist.add( source, list_item )

    xbmcPlayer = xbmc.Player()
    xbmcPlayer.play(playlist)
