#!/usr/bin/env python
import sys
import signal
import argparse

#signal.signal(signal.SIGINT, signal.SIG_DFL)

class FileChange:
    def __init__(self):
        pass

class FileChangeProdider:
    def __init__(self):
        pass

    def getChanges(self):
        return []

def mainUI():
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
    del app
    sys.exit(i_result)

def mainService():
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--service", action="store_true",
            help="enables service mode (non-UI)")
    args = parser.parse_args()

    if args.service:
        mainService()
    else:
        mainUI()
