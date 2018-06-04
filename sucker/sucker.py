#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import copy
import time
import logging
import paramiko
import ConfigParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

cfgfile = 'sucker.cfg'
filelist = []
remotedir = None
logger = None

def setlog(filenm):
    global logger
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=filenm)
    logger = logging.getLogger('sucker')
    logger.setLevel(logging.INFO)


class cfgmgr(object):
    """ read configuration file, mapping to cfg dictionary.
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
            self.rc = paramiko.Transport((host, port))
            self.rc.connect(username = user, password = pwd)

    @property
    def get_destpath(self):
        """ only consider the remote server is linux 
        """
        global cfgfile
        cfg = cfgmgr(cfgfile)
        return '/home/' + '/'.join([cfg['remote_user']] + cfg['remote_dir'].split('/')[1:])

    def transfer_file(self, flist):
        global cfgfile
        global remotedir
        # deepcopy filelist
        flist = copy.deepcopy(flist)
        if not remotedir:
            ssh = paramiko.SSHClient()
            ssh._transport = self.rc
            destpath = self.get_destpath
            stdin, stdout, stderr = ssh.exec_command('ll -d ' + destpath)
            if stdout.readline() == '':
                stdin, stdout, stderr = ssh.exec_command('mkdir -p ' + destpath)
            remotedir = destpath

        for srcpath in flist:
            filenm = os.path.basename(srcpath)
            destpath = remotedir + '/' + filenm
            try:
                sftp = paramiko.SFTPClient.from_transport(self.rc)
                sftp.put(srcpath, destpath) 
                filelist.remove(srcpath)
            except:
                cfg = cfgmgr(cfgfile)
                host, port, user, pwd = [cfg['remote_' + p] for p in ('host', 'port', 'user', 'pwd')]
                fsuckhandler = connagain(host, int(port), user, pwd)
                break
                
            logger.info("copy srcpath: %s to destpath: %s" % (srcpath, destpath))


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
        # transfer file via filelist orderly
        try:
            self.rc.transfer_file(filelist)
        except:
            pass

def connagain(host, port, user, pwd):
    cfg = cfgmgr(cfgfile)
    while True:
        try:
            rc = remoteconn(host, port, user, pwd)
            break
        except Exception as e:
            logger.info("connection to remote server failed: %s" % e)
            timeout = cfg['conntimeout']
            time.sleep(timeout)
    logger.info("connection to remote server successful")
    return filesuckhandler(rc)

def main():
    cfg = cfgmgr(cfgfile)

    logfile = cfg['logfile']
    logdir = os.path.dirname(logfile)
    if logdir and not os.path.isdir(logdir):
        os.makedirs(logdir)
    setlog(logfile)
    host, port, user, pwd = [cfg['remote_' + p] for p in ('host', 'port', 'user', 'pwd')]
    logger.info("%s@%s:%s" % (user, host, port))
    fsuckhandler = connagain(host, int(port), user, pwd)

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
