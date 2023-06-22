import cv2
import server.PyNvCodec as nvc

if __name__ == '__main__':

    cap = cv2.VideoCapture(1)

    encoder = nvc.VideoEncoder(640,480)

    with open("sample.h264", "ab") as f:
        while True:
            flag, frame_src = cap.read()
            if not flag:
                break

            bgra_frame = cv2.cvtColor(frame_src, cv2.COLOR_BGR2BGRA )
            nalu_arr = encoder.encode(bgra_frame)

            for nalu in nalu_arr:
                f.write(nalu)


            cv2.imshow('input', frame_src)
            key = cv2.waitKey(1)
            if key == ord('q'):
                break

    # 销毁内存
    cv2.destroyAllWindows()
    cap.release()
