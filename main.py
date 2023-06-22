import queue
import time

import cv2

from server.push import PushServer

if __name__ == '__main__':
    push = PushServer()
    push.start()

    # 加载人脸检测器
    faca_detector = cv2.CascadeClassifier('./haarcascade_frontalface_alt.xml')

    # 读取每一帧图像
    while True:
        try:
            frame_src = push.queue().get(block=False)

            # 将图像转化为灰度图像
            gray = cv2.cvtColor(frame_src, code=cv2.COLOR_BGR2GRAY)
            # 对每一帧灰度图像进行人脸检测
            faces = faca_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=10)
            # 深度拷贝frame
            frame_dst = frame_src.copy()
            # 对每一个检测到的人脸区域绘制检测方框
            for x, y, w, h in faces:
                cv2.rectangle(frame_dst,
                              pt1=(x, y),
                              pt2=(x + w, y + h),
                              color=[0, 0, 255],
                              thickness=2)
            # 显示检测到的结果
            cv2.imshow('input', frame_src)
            # cv2.imshow('output', frame_dst)
            # 设置显示时长
            key = cv2.waitKey(1000 // 10)  # 注意要用整除//，因为毫秒为整数
            # 按q键退出
            if key == ord('q'):
                break
        except queue.Empty:
            time.sleep(0.005)
            continue

    cv2.destroyAllWindows()
