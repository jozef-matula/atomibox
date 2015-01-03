#!/usr/bin/env python
import sys
import signal
import argparse
import time
import threading
import os
import os.path
import stat

#signal.signal(signal.SIGINT, signal.SIG_DFL)

def formatTimeStamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def logDebug(s):
    sys.stderr.write(formatTimeStamp() + " " + s + "\n")
    sys.stderr.flush()

def logError(s):
    # TODO: do something more proper
    logDebug(s)

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

class Atom:
    def __init__(self):
        # properties stored in database
        self.i_id = None
        self.i_parentId = None
        self.s_name = None
        self.f_lastModificationTimeStamp = None
        self.s_contentHash = None
        # runtime properties
        self.s_localPath = None

    def insertIntoDB(self, db):
        qi = QtSql.QSqlQuery(db);
        qi.prepare("INSERT INTO atoms(name, parentId, lastModification, contentSize, contentHash) VALUES(?, ?, ?, ?, ?)")
        qi.bindValue(0, self.s_name)
        qi.bindValue(1, self.i_parentId)
        qi.bindValue(2, self.f_lastModificationTimeStamp)
        qi.bindValue(3, self.i_contentSize if hasattr(self, 'i_contentSize') else -1)
        qi.bindValue(4, None)
        if qi.exec_():
            self.i_id = qi.lastInsertId()
            qi.finish()
        else:
            logDebug("Failed to execute insert query: %s" % str(qi.lastError().text()))

    @staticmethod
    def initDBStructures(db):
        q = QtSql.QSqlQuery(db)
        logDebug("Creating table \"atoms\"")
        if q.exec("""
                CREATE TABLE atoms(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parentId INTEGER,
                    name TEXT,
                    lastModification REAL,
                    contentSize INTEGER,
                    contentHash TEXT
                );"""):
            q.finish()
        else:
            logError("Failed to create table \"atoms\": %s" % str(q.lastError().text()))

        logDebug("Creating index \"atomParents\"")
        if(q.exec("CREATE INDEX atomParents ON atoms(parentId)")):
            q.finish()
        else:
            logError("Failed to create index \"atomParents\": %s" % str(q.lastError().text()))

    @staticmethod
    def listAtomsFromDBForParent(db, i_parentId = None):
        q = QtSql.QSqlQuery(db);
        if i_parentId is not None:
            q.prepare("SELECT * FROM atoms WHERE parentId = ?")
            q.bindValue(0, i_parentId)
        else:
            q.prepare("SELECT * FROM atoms WHERE parentId IS NULL")
        a_result = []
        if q.exec_():
            try:
                while q.next():
                    r = q.record()
                    a_result.append(Atom._createAtomFromDBRecord(r))
            finally:
                q.finish()
        return a_result

    def createAtomFromDB(db, i_id = None):
        q = QtSql.QSqlQuery(db);
        if i_id is None:
            return DirectoryAtom() # top directory
        else:
            q.prepare("SELECT * FROM atoms WHERE id = ?")
            q.bindValue(0, i_id)
        if q.exec_():
            try:
                if q.next():
                    return Atom._createAtomFromDBRecord(r)
            finally:
                q.finish()
        return None

    @staticmethod
    def _createAtomFromDBRecord(r):
        i_size = int(r.field("contentSize").value())
        if i_size < 0:
            atom = DirectoryAtom()
        else:
            atom = FileAtom()
            atom.i_contentSize = i_size
        atom.i_id = int(r.field("id").value())
        atom.s_name = str(r.field("name").value())
        v = r.field("parentId").value()
        atom.i_parentId = int(v) if len(str(v)) > 0 else None
        v = r.field("lastModification").value()
        atom.f_lastModificationTimeStamp = float(v) if len(str(v)) > 0 else None
        return atom

class DirectoryAtom(Atom):
    def __init__(self):
        Atom.__init__(self)

class FileAtom(Atom):
    def __init__(self):
        Atom.__init__(self)
        self.i_contentSize = None

class FileChangeDiscoveryThread(threading.Thread):
    def __init__(self, cfg):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.lock = threading.Lock()
        self.quitEvent = threading.Event()
        self.d_locationToDBAndAtom = {}
        logDebug("Available SQL drivers: %s" % str(QtSql.QSqlDatabase.drivers()))
        for loc in cfg.a_locations:
            logDebug("Opening database for %s" % loc.s_baseDirectoryPath)
            db = QtSql.QSqlDatabase().addDatabase("QSQLITE", "db-conn-" + loc.s_baseDirectoryPath)
            db.setDatabaseName(os.path.join(loc.s_baseDirectoryPath, ".atomibox.sqlite"));
            if db.open():
                r = db.driver().record("atoms")
                as_columnNames = [str(r.fieldName(i)) for i in range(0, r.count())]
                #logDebug("Current columns: %s" % ", ".join(as_columnNames))
                #if len(as_columnNames) and 'parent' not in as_columnNames:
                #    # do column upgrade if needed
                if len(as_columnNames) == 0:
                    Atom.initDBStructures(db)

                # TODO: move else where into run()
                atom = DirectoryAtom()
                atom.s_name = loc.s_baseDirectoryPath
                atom.s_localPath = os.path.abspath(loc.s_baseDirectoryPath)
                self.scanDirectory(db, atom, 0)

                # TODO: this code is here just for debugging
                q = QtSql.QSqlQuery(db);
                q.exec("SELECT * FROM atoms")
                while q.next():
                    r = q.record()
                    s = ", ".join([str(r.field(i).value()) for i in range(0, r.count())])
                    logDebug("ROW %s" % s)

                logDebug("Available database tables: %s" % str(db.tables()))

                self.d_locationToDBAndAtom[loc.s_baseDirectoryPath] = (db, atom)
            else:
                logDebug("Failed to open database: %s" % str(db.lastError().text()))

    def __del__(self):
        # make sure all databases are close when this object is deleted
        for s, (db, atom) in self.d_locationToDBAndAtom.items():
            logDebug("Closing database for %s" % s)
            db.close()

    def run(self):
        logDebug("FileChangeDiscoveryThread starts...")
        while not self.quitEvent.is_set(): # .wait(timeout)
            logDebug("FileChangeDiscoveryThread loops...")
            time.sleep(1)
        logDebug("FileChangeDiscoveryThread quits...")

    def scanDirectory(self, db, parentDirectoryAtom, i_currentDepth):
        logDebug("Scanning %s" % parentDirectoryAtom.s_localPath) 

        a_currentAtoms = Atom.listAtomsFromDBForParent(db, parentDirectoryAtom.i_id)
        d_nameToAtom = {}
        for atom in a_currentAtoms:
            d_nameToAtom[atom.s_name] = atom

        for s_name in os.listdir(parentDirectoryAtom.s_localPath):
            if s_name == "." or s_name == ".." or (i_currentDepth == 0 and s_name == ".atomibox.sqlite"):
                continue
            s_path = os.path.join(parentDirectoryAtom.s_localPath, s_name)
            #assert os.stat_float_times()
            t_stat = os.stat(s_path)

            atom = None
            if s_name in d_nameToAtom:
                # record found
                atom = d_nameToAtom[s_name]
                logDebug("Record for %s FOUND in #%s as #%d" % (
                        s_name, str(parentDirectoryAtom.i_id), atom.i_id))
            else:
                # new record
                if stat.S_ISDIR(t_stat.st_mode):
                    atom = DirectoryAtom()
                else:
                    atom = FileAtom()
                    atom.i_contentSize = t_stat.st_size
                atom.s_name = s_name
                atom.i_parentId = parentDirectoryAtom.i_id
                atom.f_lastModificationTimeStamp = t_stat.st_mtime
                atom.insertIntoDB(db)
                logDebug("Record for %s not found in #%s -> created #%d" % (
                        s_name, str(parentDirectoryAtom.i_id), atom.i_id))
            atom.s_localPath = s_path

            if stat.S_ISDIR(t_stat.st_mode):
                assert isinstance(atom, DirectoryAtom)
                self.scanDirectory(db, atom, i_currentDepth + 1)

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
        logDebug("HTTPServerThread finishes...")

    def stop(self):
        self.quitEvent.set()
        if self.httpd is not None:
            self.httpd.shutdown()
        logDebug("HTTPServerThread stop requested...")
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
    #cfg.a_locations.append(ConfigurationLocation('/tmp'))
    cfg.a_locations.append(ConfigurationLocation('/utils'))
    #cfg.a_locations.append(ConfigurationLocation('/tmp2'))

    if args.service:
        from PyQt5 import QtCore
        from PyQt5 import QtSql
        app = QtCore.QCoreApplication(sys.argv)
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
