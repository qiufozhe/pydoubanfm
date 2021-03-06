# coding: utf-8
import threading
import webbrowser
from gi.repository import GLib, Gtk, GdkPixbuf
from .base import Protocol as BaseProtocol
from ..utils import Resource as res, download, notify, add_tag, stars


class Protocol(BaseProtocol):
    def __init__(self):
        BaseProtocol.__init__(self)
        self.widgets = {}
        self.builder = Gtk.Builder()
        self.builder.add_from_file(res.glade)
        self.builder.connect_signals(self)
        self.builder.get_object('window-player').show_all()
        self.init_indicator()
        self.init_kbps()

    def connectionMade(self):
        BaseProtocol.connectionMade(self)
        self.transport.write(
            'user\nstate\nvolume\nkbps\nchannels\nchannel\nplaylist\nsong')

    def on_channel(self, channel_id):
        BaseProtocol.on_channel(self, channel_id)
        self.widget_channels[self.channel_id].set_active(True)

    def on_user(self, user):
        BaseProtocol.on_user(self, user)
        self.user = user
        self.set_login_state()

    def on_login_failed(self, message):
        BaseProtocol.on_login_failed(self, message)
        self.alert(Gtk.MessageType.WARNING, '登录失败', message)

    def set_login_state(self):
        if self.user:
            label = '注销'
        else:
            label = '登录'
        self.get_widget('menu-item-login').set_label(label)
        self.get_widget('menu-item-popup-login').set_label(label)

    def on_kbps(self, kbps):
        BaseProtocol.on_kbps(self, kbps)
        self.kbps = kbps
        self.widget_kbps[kbps].set_active(True)

    def init_kbps(self):
        group = Gtk.RadioMenuItem()
        self.widget_kbps = {}
        for kbps in [64, 128, 192]:
            item = Gtk.RadioMenuItem(kbps, visible=True, group=group)
            item.connect('activate', self.set_kbps, kbps)
            self.get_widget('menu-kbps').append(item)
            self.widget_kbps[kbps] = item

    def on_channels(self, channels):
        BaseProtocol.on_channels(self, channels)
        group = Gtk.RadioMenuItem()
        self.widget_channels = {}
        for channel in channels:
            item = Gtk.RadioMenuItem(channel['name'], visible=True, group=group)
            item.connect('activate', self.select_channel, int(channel['channel_id']))
            self.get_widget('menu-channels').append(item)
            self.widget_channels[int(channel['channel_id'])] = item

    def on_playlist(self, playlist):
        BaseProtocol.on_playlist(self, playlist)
        group = Gtk.RadioMenuItem()
        menu_playlist = self.get_widget('menu-playlist')

        if hasattr(self, 'widget_playlist') and self.widget_playlist:
            for item in self.widget_playlist.values():
                menu_playlist.remove(item)
        else:
            self.widget_playlist = {}

        for index, song in enumerate(playlist):
            item = Gtk.RadioMenuItem('%s - %s' % (song['artist'], song['title']), visible=True, group=group)
            item.connect('activate', self.goto, index + 1)
            menu_playlist.append(item)
            self.widget_playlist[index + 1] = item

    def goto(self, widget, index):
        if widget.get_active() and self.song['index'] != index:
            self.transport.write('goto %s' % index)

    def playback(self, widget):
        if self.get_widget('button-playback').get_tooltip_text() == '播放':
            self.transport.write('resume')
        else:
            self.transport.write('pause')

    def on_state(self, state):
        BaseProtocol.on_state(self, state)
        if state == 'paused':
            self.on_pause()
        else:
            self.on_resume()

    def rate(self, widget):
        if not self.rate_flag:
            if self.song['like']:
                self.transport.write('unlike')
            else:
                self.transport.write('like')

    def skip(self, widget):
        self.transport.write('skip')

    def on_skip(self):
        BaseProtocol.on_skip(self)

    def on_play(self, song):
        BaseProtocol.on_play(self, song)

    def on_song(self, song):
        BaseProtocol.on_song(self, song)
        self.widget_playlist[song['index']].set_active(True)
        self.get_widget('image-album-cover').set_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(
                song['picture_file'], 240, -1, True))
        self.get_widget('image-album-cover').set_tooltip_text(
            '艺术家：%s\n标　题：%s\n专　辑：%s' % (
                song['artist'],
                song['title'],
                song['albumtitle']))
        self.get_widget('menu-item-title').set_label(
            self.song['artist'] + ' - ' + self.song['title'])

        if song['like']:
            self.set_like()
        else:
            self.set_unlike()

    def on_like(self):
        BaseProtocol.on_like(self)
        self.set_like()

    def on_unlike(self):
        BaseProtocol.on_unlike(self)
        self.set_unlike()

    def set_like(self):
        self.song['like'] = True
        self.get_widget('button-rate').set_tooltip_text('取消喜欢')
        self.get_widget('menu-item-rate').set_label('取消喜欢')
        self.rate_flag = True
        self.get_widget('button-rate').set_active(True)
        self.rate_flag = False

    def set_unlike(self):
        self.song['like'] = False
        self.get_widget('button-rate').set_tooltip_text('喜欢')
        self.get_widget('menu-item-rate').set_label('喜欢')
        self.rate_flag = True
        self.get_widget('button-rate').set_active(False)
        self.rate_flag = False

    def on_pause(self):
        BaseProtocol.on_pause(self)
        self.get_widget('button-playback').set_image(
            self.get_widget('image-play'))
        self.get_widget('button-playback').set_tooltip_text('播放')
        self.get_widget('menu-item-playback').set_label('播放')

    def on_volume(self, volume):
        BaseProtocol.on_volume(self, volume)
        self.volume = float(volume)
        self.get_widget('volume-button').set_value(self.volume)

    def set_volume(self, widget, value):
        if self.volume != value:
            self.transport.write('volume %s' % value)

    def on_resume(self):
        BaseProtocol.on_resume(self)
        self.get_widget('button-playback').set_image(
            self.get_widget('image-pause'))
        self.get_widget('button-playback').set_tooltip_text('暂停')
        self.get_widget('menu-item-playback').set_label('暂停')

    def select_channel(self, widget, channel_id):
        if widget.get_active() and self.channel_id != channel_id:
            self.transport.write('channel %s' % channel_id)

    def set_kbps(self, widget, kbps):
        if widget.get_active() and self.kbps != kbps:
            self.transport.write('kbps %s' % kbps)

    def open_album(self, widget):
        webbrowser.open('http://music.douban.com' + self.song['album'])

    def album_cover_clicked(self, widget, event):
        """点击专辑封面弹出右键菜单"""
        if event.button == 3:
            self.get_widget('menu-popup').popup(
                None, None, None, None, event.button, event.time)

    def open_download_dialog(self, widget):
        dialog = Gtk.FileChooserDialog('下载', None, Gtk.FileChooserAction.SAVE, (
            '取消', Gtk.ResponseType.CANCEL,
            '确定', Gtk.ResponseType.OK))
        dialog.set_current_name(
            self.song['artist'] + ' - ' + self.song['title'] + '.mp3')
        dialog.set_current_folder(
            GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD))
        if dialog.run() == Gtk.ResponseType.OK:
            threading.Thread(target=self.download, args=(dialog.get_filename(),)).start()
        dialog.destroy()

    def download(self, filename):
        download(self.song['url'], filename)
        add_tag(filename, self.song)
        notify('下载完成', filename)

    def show_login_window(self, widget):
        if self.user:
            self.transport.write('logout')
        else:
            self.get_widget('window-login').show_all()

    def hide_login_window(self, widget, event):
        self.get_widget('window-login').hide()
        return True

    def do_login(self, widget):
        self.transport.write('login %s %s' % (
            self.get_widget('entry-email').get_text(),
            self.get_widget('entry-password').get_text()))

    def remove(self, widget):
        self.transport.write('remove')

    def on_login_success(self, user):
        BaseProtocol.on_login_success(self, user)
        self.user = user
        self.set_login_state()
        self.get_widget('window-login').hide()

    def on_logout(self):
        BaseProtocol.on_logout(self)
        self.user = None
        self.set_login_state()

    def init_indicator(self):
        try:
            from gi.repository import AppIndicator3

            self.indicator = AppIndicator3.Indicator.new(
                __name__, 'applications-multimedia',
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_icon(res.icon)
            self.indicator.set_menu(self.get_widget('indicator-menu'))
        except ImportError:
            pass

    def get_widget(self, name):
        if name not in self.widgets:
            self.widgets[name] = self.builder.get_object(name)
        return self.widgets[name]

    def exit(self, *args):
        dialog = Gtk.MessageDialog(
            None, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.YES_NO, '是否关闭播放服务？')
        if dialog.run() == Gtk.ResponseType.YES:
            self.transport.write('exit')
        else:
            dialog.destroy()
            Gtk.main_quit(*args)

    @staticmethod
    def alert(alert_type, title, message):
        """显示一个仅有确定按钮的提示框
        :param alert_type: Gtk.MessageType
        """
        dialog = Gtk.MessageDialog(
            None, 0, alert_type, Gtk.ButtonsType.OK, title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
