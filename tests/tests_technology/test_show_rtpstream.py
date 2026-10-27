import cv2
import sys

print(cv2.getBuildInformation())

def receive_stream():
    # GStreamer pipeline to receive the UDP stream, parse RTP, decode H.264,
    # and hand the frames over to OpenCV.
    
    # Note: The 'caps' (capabilities) string is crucial. It must match the stream.
    # - payload=96 matches the 'pt=96' in your sender command.
    # - clock-rate=90000 is standard for H.264.
    # - encoding-name=H264 tells it what codec to expect.
    
    gstreamer_pipeline = (
        "udpsrc port=9000 ! "
        "application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264, payload=(int)96 ! "
        "rtph264depay ! "
        "avdec_h264 ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! "
        "appsink drop=true"
    )

    gstreamer_pipeline3 = (
        "udpsrc port=9000 ! "
        "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! "
        "rtph264depay ! "
        "avdec_h264 ! "
        "videoconvert ! "
        "video/x-raw, format=BGR ! "
        "appsink drop=true"
    )

    gstreamer_pipeline2 = "udpsrc port=9000 ! application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! autovideosink"

    # Create a VideoCapture object with the GStreamer pipeline
    cap = cv2.VideoCapture(gstreamer_pipeline3, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Error: Could not open video stream.")
        print("Please check if GStreamer is installed correctly with all necessary plugins.")
        sys.exit()

    print("Successfully opened video stream. Press 'q' to quit.")

    while True:
        # Read a frame from the stream
        ret, frame = cap.read()

        # If the frame was not read successfully, break the loop
        if not ret:
            print("Stream ended or error reading frame.")
            break

        # Display the resulting frame
        cv2.imshow('H.264 UDP Stream', frame)

        # Press 'q' on the keyboard to exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything is done, release the capture and destroy windows
    print("Cleaning up and closing...")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    receive_stream()