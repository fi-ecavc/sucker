#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import time
import logging
import paramiko
import ConfigParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('sucker')
logger.setLevel(logging.INFO)


class remoteconn(object):
    """create a connection and transfer file to remote server via paramiko module
    """
    _singleton = None
    def __new__(cls, *args, **kw):
        if not cls._singleton:
            cls._singleton = super(remoteconn, cls).__new__(cls)
        return cls._singleton

    def __init__(self, host, port, user, pwd):
        try:
            self.rc = paramiko.Transport((host, port))
            self.rc.connect(username = user, password = pwd)
            self._isconn = True
        except Exception:
            self._isconn = False
            logger.debug("remote connection to remote server failed")

    @property
    def get_destpath(self):
        # todo: get the info of remote server via config file
        return "/home/vcs/testfsuck" 

    def transfer_file(self, srcpath):
        filenm = os.path.split(srcpath)[1]
        # judge the remote server is linux or windows
        if self.get_destpath.startswith('/'):
            destpath = self.get_destpath + '/' + filenm
        else:
            destpath = self.get_destpath + '\\' + filenm
        logger.debug("copy srcpath: %s to destpath: %s" % (srcpath, destpath))
        sftp = paramiko.SFTPClient.from_transport(self.rc)
        sftp.put(srcpath, destpath) 


class filesuckhandler(FileSystemEventHandler):
    """ watchdog event handler 
        upload new created file to remote server from localhost when watchdog detect the monitor path generate new file
    """
    def __init__(self, rc, *args, **kw):
        super(filesuckhandler, self).__init__()
        self.rc = rc

    def on_created(self, event):
        self.rc.transfer_file(event.src_path)


def main():
    # todo: get the info of remote server via config file
    monpath="E:\\testfsuck"
    host, port, user, pwd = ("192.168.137.3", 22, "vcs", "vcs")
    rc = remoteconn(host, port, user, pwd)
    fsuckhandler = filesuckhandler(rc)

    observer = Observer()
    observer.schedule(fsuckhandler, monpath, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 


if __name__ == "__main__":
    main()
