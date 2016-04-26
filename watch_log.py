import subprocess
import time
import threading
import tornado.web
import tornado.ioloop
import tornado.websocket


root_path = '/vagrant/'
all_log_path = root_path + '/logs/all_log'


class SocketHandler(tornado.websocket.WebSocketHandler):

    watch_log_thread = None
    send_msg_thread = None
    thread_stop = False
    clients = set()
    msg_list = []
    lock = threading.Lock()
    start_time = time.time()

    def open(self):
        SocketHandler.clients.add(self)
        SocketHandler.thread_stop = False
        if SocketHandler.watch_log_thread is None:
            def watch_log():
                print('Thread WatchLog start.')
                popen = subprocess.Popen('tail -f ' + all_log_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

                line = popen.stdout.readline().strip()

                while True:
                    if SocketHandler.thread_stop is True:
                        break

                    line = popen.stdout.readline().strip()

                    # 判断内容是否为空
                    if line:
                        SocketHandler.lock.acquire()
                        try:
                            SocketHandler.msg_list.append(line.decode())
                        finally:
                            SocketHandler.lock.release()
                print('Thread WatchLog stop.')

            def send_msg_to_client():
                print('Thread SendMsg start.')
                while True:
                    if SocketHandler.thread_stop is True:
                        break

                    end_time_interval = time.time() - SocketHandler.start_time
                    if len(SocketHandler.msg_list) > 0 and ( len(SocketHandler.msg_list) > 20 or end_time_interval > 20 ):
                        send_message = '<br/>'.join(SocketHandler.msg_list)
                        SocketHandler.start_time = time.time()
                        SocketHandler.lock.acquire()
                        try:
                            SocketHandler.msg_list.clear()
                        finally:
                            SocketHandler.lock.release()
                        for c in SocketHandler.clients:
                            c.write_message(send_message)

                    time.sleep(3)
                print('Thread SendMsg stop.')


            SocketHandler.watch_log_thread = threading.Thread(target=watch_log, name='WatchLog')
            SocketHandler.watch_log_thread.start()
            SocketHandler.send_msg_thread = threading.Thread(target=send_msg_to_client, name='SendMsg')
            SocketHandler.send_msg_thread.start()

    def on_close(self):
        SocketHandler.clients.remove(self)
        if len(SocketHandler.clients) == 0:
            SocketHandler.thread_stop = True
            subprocess.Popen('echo "" >> ' + all_log_path, shell=True)
            SocketHandler.watch_log_thread.join()
            SocketHandler.watch_log_thread = None
            SocketHandler.send_msg_thread.join()
            SocketHandler.send_msg_thread = None

    def on_message(self, message):
        date, city, command = message.split(',')
        subprocess_command = 'python {root_path}manage.py {command} {date} {city}'.format(
            root_path=root_path,
            command=command,
            date=date,
            city=city,
        )
        subprocess.Popen(
            subprocess_command,
            shell=True,
            cwd=(root_path + 'log/')
        )


class Index(tornado.web.RequestHandler):
    def get(self):
        self.render('templates/index.html')

if __name__ == '__main__':
    app = tornado.web.Application([
        ('/', Index),
        ('/soc', SocketHandler),
    ])
    app.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
