import threading
import struct
import time

import cv2
import numpy as np

from twisted.internet import reactor, protocol
from twisted.internet.protocol import connectionDone
from twisted.python import failure

import server.PyNvCodec as nvc

class AbortThread(Exception):
    pass


class DataProvider:
    def __init__(self):
        self.buffer = bytearray()
        self.lock = threading.Lock()
        self.isOpen = True

    def push(self, data):
        self.lock.acquire()
        self.buffer.extend(data)
        self.lock.release()

    def read(self, size):
        data = []
        while len(data) == 0 and self.isOpen:
            self.lock.acquire()
            length = min(len(self.buffer), size)
            data = bytes(self.buffer[:length])
            self.buffer = self.buffer[length:]
            self.lock.release()
            time.sleep(0.005)

        if not self.isOpen:
            raise AbortThread
        return data

    def close(self):
        self.isOpen = False


class PushProtocol(protocol.Protocol):
    MAX_LENGTH = 1024 * 1024  # 最大 1M

    def __init__(self, provider: DataProvider,connections):
        self.buffer = bytearray()
        self.provider = provider
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
        self.provider.push(data)
        # self.transport.write(data)

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
    def __init__(self, provider: DataProvider):
        self.provider = provider
        self.pushConnection = []

    def buildProtocol(self, addr):
        return PushProtocol(self.provider, self.pushConnection)


class PushServer:
    def __init__(self, provider: DataProvider):
        self.provider = provider
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.start_twisted)
        self.thread.start()
        print("PushServer start")

    def stop(self):
        reactor.stop()
        self.thread.join()
        print("PushServer stop")

    def start_twisted(self):
        reactor.listenTCP(8020, PushFactory(self.provider))
        reactor.run(installSignalHandlers=False)


class PushDecoder:
    def __init__(self, provider: DataProvider):
        self.provider = provider
        self.thread = None
        self.bufferFrame = None
        self.bufferLock = threading.Lock()

    def getFrame(self):
        img = None
        self.bufferLock.acquire()
        if self.bufferFrame is not None:
            img = np.copy(self.bufferFrame)
            self.bufferFrame = None
        self.bufferLock.release()
        return img

    def start(self):
        self.thread = threading.Thread(target=self.decoder)
        self.thread.start()
        print("PushDecoder start")

    def decoder(self):
        import av
        try:
            video = av.open(self.provider, 'r')
            for frame in video.decode():
                yuv_frame = frame.to_ndarray()
                #rgb_frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2BGR_I420)
                #rgb_frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2BGR_YV12)
                #rgb_frame = np.rot90(rgb_frame, k=1)
                # rgb_frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV420sp2BGR)
                # rgb_frame = np.rot90(rgb_frame, k=1)
                #rgb_frame = np.fliplr(rgb_frame)
                rgb_frame = self.mobile_handler(yuv_frame)
                self.bufferLock.acquire()
                self.bufferFrame = np.copy(rgb_frame)
                self.bufferLock.release()
        except AbortThread:
            pass
        except Exception as e:
            pass

    def mobile_handler(self,yuv_frame):
        rgb_frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2BGR_YV12)
        rgb_frame = np.rot90(rgb_frame, k=1)
        rgb_frame = np.fliplr(rgb_frame)
        return rgb_frame

    def stop(self):
        self.provider.close()
        self.thread.join()
        print("PushDecoder stop")
