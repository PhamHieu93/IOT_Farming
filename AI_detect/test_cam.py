import cv2
import sys

def test_camera():
    # Khởi tạo capture từ camera (0 là camera mặc định)
    cap = cv2.VideoCapture(0)
    
    # Kiểm tra xem camera có được mở thành công không
    if not cap.isOpened():
        print("Không thể mở camera")
        sys.exit()

    print("Camera đã được mở thành công!")
    
    while True:
        # Đọc frame từ camera
        ret, frame = cap.read()
        
        # Kiểm tra xem frame có được đọc thành công không
        if not ret:
            print("Không thể nhận frame từ camera. Thoát...")
            break
        
        # Hiển thị frame
        cv2.imshow('Camera Test', frame)
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) == ord('q'):
            break
    
    # Giải phóng camera và đóng cửa sổ
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_camera()