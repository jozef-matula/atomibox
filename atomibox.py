import sys
import signal
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

#signal.signal(signal.SIGINT, signal.SIG_DFL)

class FileChange:
    def __init__(self):
        pass

class FileChangeProdider:
    def __init__(self):
        pass

    def getChanges(self):
        return []

def onQuit():
    QtCore.QCoreApplication.instance().quit()

def main():
    app = QtWidgets.QApplication(sys.argv)

    w = QtWidgets.QWidget()

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

if __name__ == '__main__':
    main()
