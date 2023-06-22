import cv2
import numpy as np
import server.PyNvCodec as nvc

if __name__ == '__main__':

    cap = cv2.VideoCapture(1)

    width = 640
    height = 480

    encoder = nvc.VideoEncoder(640, 480)
    decoder = nvc.VideoDecoder()

    n=0
    while True:
        flag, frame_src = cap.read()
        if not flag:
            break

        n=n+1
        frame_src = cv2.putText(frame_src, 'frame {}'.format(n), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow('src', frame_src)

        bgra_frame = cv2.cvtColor(frame_src, cv2.COLOR_BGR2BGRA )
        nalu_arr = encoder.encode(bgra_frame)

        for nalu in nalu_arr:
            yuv_frames = decoder.decode(nalu)
            for yuv_bytes in yuv_frames:

                yuv_np = np.frombuffer(yuv_bytes, dtype=np.uint8)
                yuv_reshaped = yuv_np.reshape((int(height * 1.5), width))

                bgr_frame = cv2.cvtColor(yuv_reshaped, cv2.COLOR_YUV2BGR_NV21)

                cv2.imshow('decode', bgr_frame)
                # 设置显示时长
                key = cv2.waitKey(1)  # 注意要用整除//，因为毫秒为整数
                # 按q键退出
                if key == ord('q'):
                    break

    # 销毁内存
    cv2.destroyAllWindows()
    cap.release()
    nvc.release()
