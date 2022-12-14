from bs4 import BeautifulSoup
import requests
import posixpath
import re
from pystray import MenuItem
import pystray
from PIL import Image
from threading import Thread
import time
import webbrowser
import os, sys
import traceback
import logging
logging.basicConfig(level=logging.ERROR)

# pyinstaller --onefile --windowed -i=icon.ico --add-data="icon.ico;." main.py

id_parser = re.compile('.*/(?P<id>\d+)')

def get_url(channel_id, page):
    return posixpath.join('https://tgd.kr/s/', channel_id, 'page', str(page))

def get_articles(channel_id, page=1):
    while True:
        got = requests.get(get_url(channel_id, page=page))
        if got.status_code != 200:
            print(got.status_code)
            continue
        soup = BeautifulSoup(got.content, 'html.parser')
        header = soup.select_one('head > title').get_text().strip()
        thumbnail = soup.select_one('#board-info > img').attrs['src'].strip()
        break
    return list(map(lambda x : dict(
            channel_id = channel_id,
            header = header,
            thumbnail = thumbnail,
            id = id_parser.search(x.select_one('a[title]').attrs['href'].strip()).group('id').strip(),
            href = f'https://tgd.kr/s/{channel_id}/' + id_parser.search(x.select_one('a[title]').attrs['href'].strip()).group('id').strip(),
            title = x.select_one('a[title]').attrs['title'].strip(),
            reply = x.select_one('div.list-title > small').get_text().strip() if x.select_one('div.list-title > small') != None else '',
            author = x.select_one('div.list-writer span').get_text().strip(),
            datetime = x.select_one('div.list-time').get_text().strip(),
            admin = x.select_one('img[alt=Broadcaster]') != None
            ), soup.select('#article-list [id|=article-list-row]:not(.notice)')))

def make_toast(article):
    import winsdk.windows.ui.notifications as notifications
    import winsdk.windows.data.xml.dom as dom
    import urllib.request
    
    app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
    #this_file = inspect.getfile(inspect.currentframe())
    #if this_file[-4:] == '.exe':
    #    app = this_file
        
    #print(this_file, this_file[-4:], app, __file__, sys.executable)
    #app = sys.executable
    app = r'Microsoft.Windows.Shell.RunDialog'
    app = 'Chrome'

    #create notifier
    nManager = notifications.ToastNotificationManager
    notifier = nManager.create_toast_notifier(app)    

    try:
        urllib.request.urlretrieve(article['thumbnail'], f"{article['channel_id']}.png")
    except:
        pass

    #define your notification as string
    tString = f"""
        <toast>  
          <visual>
            <binding template="ToastGeneric">
              <image placement="appLogoOverride" hint-crop="circle" src="{os.getcwd()}/{article['channel_id']}.png"/>
              <text>{article['header']}</text>
              <text>{article['title']}</text>
              <text>{article['author']} - {article['datetime']}</text>
            </binding>
          </visual>
        </toast>
    """

    def handle_activated(notification, _):
        webbrowser.open(notification.tag, new=2)

    #convert notification to an XmlDocument
    xDoc = dom.XmlDocument()
    xDoc.load_xml(tString)

    #display notification
    notification = notifications.ToastNotification(xDoc)
    notification.tag = article['href']
    notification.add_activated(handle_activated)
    notifier.show(notification)


def main_thread():
    global is_running, recent, is_print_log
    recent = {}

    while True:
        if is_running:
            try:
                for e in spectators:
                    articles = get_articles(e)
                    if is_print_log:
                        with open('log.txt', 'a', encoding='utf8') as log:
                            log.write(f'??????: {e} => ?????????: {articles[0]["id"]} {articles[0]["title"]} / ????????? ?????? ??????: {recent[e]["id"]} {recent[e]["title"]} \n')
                    if e not in recent:
                        recent[e] = articles[0]
                        with open('log.txt', 'a', encoding='utf8') as log:
                            log.write(f'?????????: {e} => {articles[0]["id"]} {articles[0]["title"]} \n')
                    else:
                        for article in reversed(articles):
                            if article['id'] > recent[e]['id']:
                                with open('log.txt', 'a', encoding='utf8') as log:
                                    log.write(f'????????? ??????: {e} => {article["id"]} {article["title"]} \n')
                                make_toast(article)
                                recent[e] = article
                        if articles[0]['id'] != recent[e]['id']:
                            with open('log.txt', 'a', encoding='utf8') as log:
                                log.write(f'?????? ?????? ????????? ??????: {e} => {article["id"]} {article["title"]} \n')
            except Exception as err:
                with open('log.txt', 'a', encoding='utf8') as log:
                    logging.error(traceback.format_exc())
                    log.write(traceback.format_exc() + '\n')
        for i in range(1, 100+1):
            time.sleep(0.1)

def exit_app():
    tray.stop()

def menu_pause():
    global is_running
    is_running = not is_running
    tray.update_menu()

def make_func(x):
    return lambda: webbrowser.open(x, new=2)

def debug_init_recent():
    global recent
    recent['yo4ri']['id'] = '0'

def debug_change_menu():
    global is_print_log
    is_print_log = not is_print_log
    tray.update_menu()

if __name__ == '__main__':
    is_print_log = False
    is_running = True
    recent = {}
    
    spectators = []
    if not os.path.isfile('ids.txt'):
        with open('ids.txt', 'wt', encoding='utf8') as spec_file:
            spec_file.write("""yo4ri
steelohs

# ????????? ???????????? ????????? ???????????? ????????? ????????? ????????????.
"""
                )
        
    with open('ids.txt', 'rt', encoding='utf8') as spec_file:
        while True:
            this_line = spec_file.readline().strip()
            if this_line == '':
                break
            if not this_line.startswith('#') and len(this_line) > 0:
                spectators.append(this_line)

    tray_icon = Image.open(os.path.join(os.path.dirname(__file__), 'icon.ico'))
    tray_menu = []
    tray_menu.append(MenuItem('????????? ??????????????????', menu_pause, checked=lambda x: not is_running))
    tray_menu.append(pystray.Menu.SEPARATOR)
    tray_menu.append(MenuItem('==????????? ????????????==', None, enabled=lambda x: False))
    for e in spectators:
        e_url = 'https://tgd.kr/s/' + e
        tray_menu.append(MenuItem(e, make_func(e_url)))
    tray_menu.append(pystray.Menu.SEPARATOR)
    #tray_menu.append(MenuItem('?????????: ?????????', debug_init_recent))
    #tray_menu.append(MenuItem('?????????: ?????? ??????', debug_change_menu, checked=lambda x: is_print_log))
    tray_menu.append(MenuItem('??????', exit_app))
    
    tray_menu = tuple(tray_menu)
    tray = pystray.Icon('????????? ?????????', tray_icon, '????????? ?????????', tray_menu)
    
    Thread(target=main_thread, daemon=True).start()
    
    tray.run()
            
    sys.exit()

    











































    
