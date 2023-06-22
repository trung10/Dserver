import queue
import threading
import struct
import time

import cv2
import numpy as np

from twisted.internet import reactor, protocol
from twisted.internet.protocol import connectionDone
from twisted.python import failure

import server.PyNvCodec as nvc


class PushProtocol(protocol.Protocol):
    MAX_LENGTH = 1024 * 1024  # 最大 1M

    def __init__(self, q, connections):
        self.buffer = bytearray()
        self.queue = q
        self.pushConnection = connections
        self.pushType = 0  # 0: 电脑端, 1: 手机端

    def connectionMade(self):
        if len(self.pushConnection) == 0:
            print('Push connected:', self.transport.client)
            self.pushConnection.append(self.transport)
        else:
            self.transport.loseConnection()

    def connectionLost(self, reason: failure.Failure = connectionDone):
        if self.transport in self.pushConnection:
            self.pushConnection.remove(self.transport)
            print('Push disconnected:', self.transport.client)

    def dataReceived(self, data):
        # print("dataReceived", len(data))
        self.buffer.extend(data)

        packet, offset = self.getPacket(self.buffer)
        if packet is not None:
            self.packetReceived(packet)
            self.buffer = self.buffer[offset:]

    def packetReceived(self, data):
        cmd_id, = struct.unpack('>I', data[:4])
        if cmd_id == 1:
            self.frameReceived(data[4:])
        elif cmd_id == 2:
            self.typeReceived(data[4:])
        else:
            print("Unknown cmdId:", cmd_id)
            self.transport.loseConnection()

    def typeReceived(self, data):
        self.pushType = data[0]

    def frameReceived(self, data):
        # print("dataReceived", len(data))
        frames = nvc.decode(data)
        for frame in frames:
            self.queue.put(frame)

    def validateLength(self, length):
        if length > self.MAX_LENGTH:
            print("Data length too large")
            self.transport.loseConnection()
            return False
        return True

    def getPacket(self, data):
        length, cmd_id, = struct.unpack('>II', data[:8])
        # print("Data length is:", length)
        if self.validateLength(length):
            if len(data[8:]) < length:
                return None, None
            return data[4:length + 8], length + 8
        else:
            return None, None


class PushFactory(protocol.Factory):
    def __init__(self):
        self.queue = queue.Queue()
        self.pushConnection = []

    def buildProtocol(self, addr):
        self.queue = queue.Queue()
        return PushProtocol(self.queue, self.pushConnection)


class PushServer:
    def __init__(self):
        self.factory = PushFactory()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.start_twisted)
        self.thread.start()
        print("PushServer start")

    def stop(self):
        reactor.stop()
        self.thread.join()
        print("PushServer stop")

    def queue(self):
        return self.factory.queue

    def start_twisted(self):
        nvc.init(1280,720)
        reactor.listenTCP(8020, self.factory)
        reactor.run(installSignalHandlers=False)
        nvc.release()