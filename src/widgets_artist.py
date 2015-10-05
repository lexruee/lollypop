# Copyright (c) 2014-2015 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GdkPixbuf, GLib, Gio

from threading import Thread
from cgi import escape
from os import mkdir, path

try:
    from lollypop.wikipedia import Wikipedia
except:
    pass
from lollypop.define import Lp


class ArtistContent(Gtk.Stack):
    """
        Widget showing artist image and bio
    """

    _CACHE_PATH = path.expanduser("~") + "/.local/share/lollypop/infos"

    def __init__(self):
        """
            Init artist content
        """
        Gtk.Stack.__init__(self)
        self._artist = ''
        self.set_transition_duration(500)
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ArtistContent.ui')
        self._content = builder.get_object('content')
        self._image = builder.get_object('image')
        self._image_frame = builder.get_object('frame')
        self.add_named(builder.get_object('widget'), 'widget')
        self.add_named(builder.get_object('notfound'), 'notfound')
        self.add_named(builder.get_object('spinner'), 'spinner')
        if not path.exists(self._CACHE_PATH):
            try:
                mkdir(self._CACHE_PATH)
            except:
                print("Can't create %s" % self._CACHE_PATH)

    def get_artist(self):
        """
            Get current artist
            @return artist as str
        """
        return self._artist

    def clear(self):
        """
            Clear content
        """
        self._content.set_text('')
        self._image_frame.hide()
        self._image.clear()
        self.set_visible_child_name('spinner')

    def populate(self, artist, content, image_url, suffix):
        """
            populate widget with content
            @param artist as string
            @param content as string
            @param image url as string
            @param suffix as string
            @thread safe
        """
        try:
            data = None
            stream = None
            if content is not None:
                if image_url is not None:
                    f = Gio.File.new_for_uri(image_url)
                    (status, data, tag) = f.load_contents()
                    if status:
                        stream = Gio.MemoryInputStream.new_from_data(data,
                                                                     None)
                self._save_to_cache(artist, content, data, suffix)
            GLib.idle_add(self._set_content, content, stream)
        except Exception as e:
            print("ArtistContent::populate: %s" % e)

    def uncache(self, artist, suffix):
        """
            Remove artist from cache
            @param artist as string
            @param suffix as string
        """
        filepath = "%s/%s_%s.txt" % (self._CACHE_PATH,
                                     "".join(
                                        [c for c in artist if
                                         c.isalpha() or
                                         c.isdigit() or c == ' ']).rstrip(),
                                     suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass
        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        f = Gio.File.new_for_path(filepath)
        try:
            f.delete(None)
        except:
            pass

#######################
# PRIVATE             #
#######################
    def _set_content(self, content, stream):
        """
            Set content
            @param content as string
            @param data as Gio.MemoryInputStream
        """
        # Happens if widget is destroyed while loading content from the web
        if self.get_child_by_name('widget') is None:
            return
        if content is not None:
            self._content.set_markup(escape(content))
            if stream is not None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream,
                                                                   200,
                                                                   -1,
                                                                   True,
                                                                   None)
                self._image.set_from_pixbuf(pixbuf)
                del pixbuf
                self._image_frame.show()
            self.set_visible_child_name('widget')
        else:
            self.set_visible_child_name('notfound')

    def _save_to_cache(self, artist, content, data, suffix):
        """
            Save data to cache
            @param content as string
            @param data as bytes
            @param suffix as string
        """
        if content is None:
            return

        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        f = Gio.File.new_for_path(filepath+".txt")
        fstream = f.replace(None, False,
                            Gio.FileCreateFlags.REPLACE_DESTINATION, None)
        if fstream is not None:
            fstream.write(content.encode(encoding='UTF-8'), None)
            fstream.close()
        if data is not None:
            f = Gio.File.new_for_path(filepath)
            fstream = f.replace(None, False,
                                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
            if fstream is not None:
                fstream.write(data, None)
                fstream.close()

    def _load_from_cache(self, artist, suffix):
        """
            Load content from cache
            @return (content as string, data as bytes)
        """
        filepath = "%s/%s_%s" % (self._CACHE_PATH,
                                 "".join([c for c in artist if
                                          c.isalpha() or
                                          c.isdigit() or c == ' ']).rstrip(),
                                 suffix)
        content = None
        data = None
        if path.exists(filepath+".txt"):
            f = Gio.File.new_for_path(filepath+".txt")
            (status, content, tag) = f.load_contents()
            if status and path.exists(filepath):
                f = Gio.File.new_for_path(filepath)
                (status, data, tag) = f.load_contents()
                if not status:
                    data = None
        if content is None:
            return (None, None)
        else:
            return (content.decode("utf-8"), data)


class WikipediaContent(ArtistContent):
    """
        Show wikipedia content
    """

    def __init__(self, menu):
        """
            Init widget
            @param menu as Gtk.MenuButton
        """
        ArtistContent.__init__(self)
        self._menu = menu
        self._app = Gio.Application.get_default()

    def populate(self, artist):
        """
            Populate content
            @param artist as str
            @thread safe
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        self._artist = artist
        if not self._load_cache_content(artist):
            self._load_page_content(artist)
            self._setup_menu(artist)

    def uncache(self, artist):
        """
            Remove artist from cache
            @param artist as string
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        ArtistContent.uncache(self, artist, 'wikipedia')

#######################
# PRIVATE             #
#######################
    def _load_cache_content(self, artist):
        """
            Load from cache
            @param artist as str
            @return True if loaded
        """
        (content, data) = self._load_from_cache(artist, 'wikipedia')
        if content:
            stream = None
            if data is not None:
                stream = Gio.MemoryInputStream.new_from_data(data, None)
            GLib.idle_add(self._set_content, content, stream)
            return True
        return False

    def _load_page_content(self, page):
        """
            Load page content
            @param page as str
        """
        wp = Wikipedia()
        (url, image_url, content) = wp.get_page_infos(page)
        ArtistContent.populate(self, self._artist, content,
                               image_url, 'wikipedia')

    def _setup_menu(self, artist):
        """
            Setup menu for artist
        """
        wp = Wikipedia()
        GLib.idle_add(self._setup_menu_strings, [artist])
        search = wp.search(artist)
        GLib.idle_add(self._setup_menu_strings, search)

    def _setup_menu_strings(self, strings):
        """
            Setup a menu with strings
            @param strings as [str]
        """
        menu_model = Gio.Menu()
        i = 0
        for string in strings:
            action = Gio.SimpleAction(name="wikipedia_%s" % i)
            self._app.add_action(action)
            action.connect('activate',
                           self._on_search_activated,
                           string)
            menu_model.append(string, "app.wikipedia_%s" % i)
            i += 1
        self._menu.set_menu_model(menu_model)
        self._menu.show()

    def _on_search_activated(self, action, variant, page):
        """
            Switch to page
            @param SimpleAction
            @param GVariant
        """
        self.uncache(self._artist)
        self.clear()
        t = Thread(target=self._load_page_content, args=(page,))
        t.daemon = True
        t.start()


class LastfmContent(ArtistContent):
    """
        Show lastfm content
    """

    def __init__(self):
        """
            Init widget
        """
        ArtistContent.__init__(self)

    def populate(self, artist):
        """
            Populate content
            @param artist as string
            @thread safe
        """
        content = None
        if artist is None:
            artist = Lp.player.get_current_artist()
        self._artist = artist
        (content, data) = self._load_from_cache(artist, 'lastfm')
        if content:
            stream = None
            if data is not None:
                stream = Gio.MemoryInputStream.new_from_data(data, None)
            GLib.idle_add(self._set_content, content, stream)
        else:
            (url, image_url, content) = Lp.lastfm.get_artist_infos(artist)
            ArtistContent.populate(self, artist, content, image_url, 'lastfm')

    def uncache(self, artist):
        """
            Remove artist from cache
            @param artist as string
        """
        if artist is None:
            artist = Lp.player.get_current_artist()
        ArtistContent.uncache(self, artist, 'lastfm')
