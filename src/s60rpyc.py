'''
Created on Jan 8, 2011

@author: Administrator
'''

import rpyc
from rpyc.core import SlaveService
from rpyc.utils.server import ThreadedServer
from rpyc.utils.classic import DEFAULT_SERVER_PORT

from threading import Thread
import Queue

import btsocket
import e32
import appuifw

try:
    import pyswinst
    inst = pyswinst.SwInst()
except ImportError:
    print "swinst extension not present."


class MyService(SlaveService):
    
    def exposed_callmain(self, cb, *args, **kwargs):
        return cg.request_call(cb, *args, **kwargs)
    
    def exposed_install(self, path, cb):
        return cg.request_call(inst.install, unicode(path), rpyc.async(cb))

class Server(Thread):
    
    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.server = ThreadedServer(MyService, 
                                     auto_register=False,
                                     port = DEFAULT_SERVER_PORT)
       
    def run(self):
        self.server.start()

class Callgate:
    
    def __init__(self):
        self._request_queue = Queue.Queue()
    
    def request_call(self, cb, *args, **kwargs):
        def f():
            return cb(*args, **kwargs)
        res_queue = Queue.Queue()
        req = f, res_queue
        self._request_queue.put_nowait(req)
        res = res_queue.get()
        return res
    
    def async_call(self, cb, *args, **kwargs):
        def f():
            return cb(*args, **kwargs)
        res_queue = Queue.Queue()
        req = f, res_queue
        self._request_queue.put_nowait(req)
 
    def run(self):
        while True:
            try:
                req = self._request_queue.get_nowait() 
            except Queue.Empty:
                e32.ao_sleep(0.5)
                continue
            if req == 1:
                break
            f, res_queue = req
            res = f()
            res_queue.put_nowait(res)
            
    def stop(self):
        self._request_queue.put_nowait(1)

def exit_key_handler():
    cg.stop()

def start_network():
    apid = None
    for ap in btsocket.access_points():
        if 'pergola' in ap['name'].lower():
            apid = ap['iapid']
            break
    if apid is not None:
        apo  = btsocket.access_point(apid)
        btsocket.set_default_access_point(apo)
        apo.start()

start_network()

srv = Server()
srv.start()

appuifw.app.exit_key_handler = exit_key_handler


cg = Callgate()
cg.run()

