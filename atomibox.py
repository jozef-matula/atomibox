#!/usr/bin/env python
import sys
import signal
import argparse
import time
import threading

#signal.signal(signal.SIGINT, signal.SIG_DFL)

def logDebug(s):
    sys.stderr.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + s + "\n")
    sys.stderr.flush()

class ConfigurationLocation:
    def __init__(self, s_baseDirectoryPath = None):
        self.s_baseDirectoryPath = s_baseDirectoryPath

class Configuration:
    def __init__(self):
        self.a_locations = []
        self.i_tcpPort = 8847

class FileChange:
    def __init__(self):
        pass

class FileChangeProdider:
    def __init__(self):
        pass

    def getChanges(self):
        return []

def mainUI(cfg):
    from PyQt5 import QtCore
    from PyQt5 import QtWidgets
    from PyQt5 import QtGui
    app = QtWidgets.QApplication(sys.argv)

    w = QtWidgets.QWidget()

    def onQuit():
        QtCore.QCoreApplication.instance().quit()

    class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
        def __init__(self, icon, parent=None):
            QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
            menu = QtWidgets.QMenu(parent)
            exitAction = menu.addAction(QtGui.QIcon("resources/quit.ico"), "E&xit")
            exitAction.triggered.connect(onQuit)
            self.setContextMenu(menu)

    trayIcon = SystemTrayIcon(QtGui.QIcon("resources/main.ico"), w)
    trayIcon.show()

    i_result = app.exec_()
    trayIcon.hide()
    del app
    sys.exit(i_result)

class FileChangeDiscoveryThread(threading.Thread):
    def __init__(self, cfg):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.lock = threading.Lock()
        self.quitEvent = threading.Event()

    def run(self):
        logDebug("FileChangeDiscoveryThread starts...")
        while not self.quitEvent.is_set(): # .wait(timeout)
            logDebug("FileChangeDiscoveryThread loops...")
            time.sleep(1)
        logDebug("FileChangeDiscoveryThread quits...")

    def stop(self):
        self.quitEvent.set()
        logDebug("FileChangeDiscoveryThread stop requested...")
        self.join()

class HTTPServerThread(threading.Thread):
    def __init__(self, cfg):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.httpd = None
        self.quitEvent = threading.Event()

    def run(self):
        logDebug("HTTPServerThread starts...")
        import http.server
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                sys.stdout.flush()
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(bytes('Hello', 'UTF-8'))
                except Exception as e:
                    self.send_error(500, "Internal server error: " + str(e))

        t_serverAddress = ('', self.cfg.i_tcpPort)
        if not self.quitEvent.is_set():
            self.httpd = http.server.HTTPServer(t_serverAddress, Handler)
            logDebug("HTTPServerThread constructed HTTPServer object")
            try:
                self.httpd.serve_forever()
            finally:
                self.httpd.socket.close()
        while not self.quitEvent.is_set(): # .wait(timeout)
            logDebug("HTTPServerThread loops and waits for quit...")
            time.sleep(1)
        logDebug("HTTPServer finishes...")

    def stop(self):
        self.quitEvent.set()
        if self.httpd is not None:
            self.httpd.shutdown()
        logDebug("HTTPServer stop requested...")
        self.join()

def mainClient(cfg):
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--service", action="store_true",
            help="enables service mode (non-UI)")
    parser.add_argument("-c", "--client", action="store_true",
            help="enables client mode (non-UI)")
    args = parser.parse_args()

    cfg = Configuration()
    cfg.a_locations.append(ConfigurationLocation('/tmp'))
    cfg.a_locations.append(ConfigurationLocation('/utils'))

    if args.service:
        discoveryThread = FileChangeDiscoveryThread(cfg)
        discoveryThread.start()
        httpdThread = HTTPServerThread(cfg)
        httpdThread.start()

        quitEvent = threading.Event()

        def sigIntHandler(signal, frame):
            logDebug("Termination requested")
            quitEvent.set()
        signal.signal(signal.SIGINT, sigIntHandler)

        while not quitEvent.wait(1):
            pass

        httpdThread.stop()
        discoveryThread.stop()
    elif args.client:
        mainClient(cfg)
    else:
        mainUI(cfg)
