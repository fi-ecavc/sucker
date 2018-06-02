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
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

filelist = []

class cfgmgr(object):
    """ read configuration file sucker.cfg, mapping to cfg dictionary.
    """
    _singleton = None
    cfg = {} 

    def __new__(cls, *args, **kw):
        if not cls._singleton:
            cls._singleton = super(cfgmgr, cls).__new__(cls)
        return cls._singleton

    def __init__(self, cfgfile):
        self.parse_cfg(cfgfile)

    @classmethod
    def parse_cfg(cls, cfgfile):
        conf = ConfigParser.ConfigParser()
        conf.read(cfgfile)
        secs = conf.sections()
        for sec in secs:
            for (nm, val) in conf.items(sec):
                cls.cfg[nm] = val

    def __getitem__(self, key):
        return self.cfg[key]
        

class remoteconn(object):
    """ create a connection and transfer file to remote server via paramiko module
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
        except Exception as e:
            logger.debug("connection to remote server failed: %s" % e)

    @property
    def get_destpath(self):
        """ only consider the remote server is linux 
        """
        cfg = cfgmgr('sucker.cfg')
        return '/home/' + '/'.join([cfg['remote_user']] + cfg['remote_dir'].split('/')[1:])

    def transfer_file(self, srcpath):
        filenm = os.path.basename(srcpath)
        destpath = self.get_destpath
        if not os.path.isdir(destpath):
            ssh = paramiko.SSHClient()
            ssh._transport = self.rc
            stdin, stdout, stderr = ssh.exec_command('mkdir -p ' + destpath)
        destpath = destpath + '/' + filenm
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
        global filelist
        filelist.append(event.src_path)
        # todo: transfer file via filelist orderly
        self.rc.transfer_file(event.src_path)


def main():
    cfg = cfgmgr('sucker.cfg')
    host, port, user, pwd = [cfg['remote_' + p] for p in ('host', 'port', 'user', 'pwd')]
    logger.debug("%s@%s:%s" % (user, host, port))
    rc = remoteconn(host, int(port), user, pwd)
    fsuckhandler = filesuckhandler(rc)

    observer = Observer()
    mondir = cfg['mondir']
    if not os.path.isdir(mondir):
        os.makedirs(mondir)
    observer.schedule(fsuckhandler, mondir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 


if __name__ == "__main__":
    main()
