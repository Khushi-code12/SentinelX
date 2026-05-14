from imageai.Detection import VideoObjectDetection
import cv2
import numpy as np
import time
import smtplib
from email.message import EmailMessage

# Turn on the camera
camera = cv2.VideoCapture(0)  # "0" means "use the default camera"
detector = VideoObjectDetection()
detector.setModelTypeAsYOLOv3()
detector.setModelPath("yolo.h5")
detector.loadModel()

while True:
    # Take a photo from the camera
    success, frame = camera.read()

    # Show the photo on screen
    cv2.imshow('Live Video', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) == ord('q'):
        break

def on_detect(frame_number, output_dict, output_count):
    # Check if BOTH "person" and "cell phone" are detected
    objects = output_dict["name"]
    if "person" in objects and "cell phone" in objects:
        print("Phone and person detected nearby! Possible snatching?")
        # Trigger alert and save video clip here

detector.detectObjectsFromVideo(
    camera_input=0,
    frames_per_second=20,
    save_detected_video=False,
    per_frame_function=on_detect
)

# Initialize background subtractor (to detect motion)
background_subtractor = cv2.createBackgroundSubtractorMOG2()

def detect_motion(frame):
    # 1. Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. Apply background subtraction
    mask = background_subtractor.apply(gray)
    
    # 3. Check if motion is detected
    if np.sum(mask) > 10000:  # Adjust this threshold based on testing
        return True  # Motion detected!
    return False  # No motion detected

def on_detect(frame_number, output_dict, output_count):
    objects = output_dict["name"]
    frame = output_dict["frame"]  # Get the current video frame
    
    if "person" in objects and "cell phone" in objects:
        if detect_motion(frame):  # Check for sudden motion
            print("ALERT: Possible phone snatching detected!")
            # Save the video clip and send an alert


# Initialize motion detector
background_subtractor = cv2.createBackgroundSubtractorMOG2()

def detect_motion(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = background_subtractor.apply(gray)
    if np.sum(mask) > 10000:  # Adjust this threshold
        return True
    return False

# Initialize video writer variables
video_writer = None
start_time = None

# Email alert function
def send_alert():
    msg = EmailMessage()
    msg['Subject'] = "Crime Detected!"
    msg['From'] = "your_email@gmail.com"
    msg['To'] = "recipient@example.com"
    msg.set_content("A phone snatching was detected!")

    # Attach the video clip
    with open('theft_clip.mp4', 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename='theft_clip.mp4')

    # Send email (use your Gmail password)
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login("your_email@gmail.com", "your_password")
        server.send_message(msg)

# Object detection callback
def on_detect(frame_number, output_dict, output_count):
    global video_writer, start_time
    frame = output_dict["frame"]
    objects = output_dict["name"]  # Fix: Get detected objects here

    if "person" in objects and "cell phone" in objects and detect_motion(frame):
        if video_writer is None:
            height, width = frame.shape[0], frame.shape[1]
            video_writer = cv2.VideoWriter('theft_clip.mp4', 
                                         cv2.VideoWriter_fourcc(*'mp4v'), 
                                         20, (width, height))
            start_time = time.time()
        
        video_writer.write(frame)
        
        if time.time() - start_time > 10:
            video_writer.release()
            video_writer = None
            send_alert()  # Now defined!

# Initialize detector
detector = VideoObjectDetection()
detector.setModelTypeAsYOLOv3()
detector.setModelPath("yolo.h5")
detector.loadModel()

# Start detection
detector.detectObjectsFromVideo(
    camera_input=0,
    frames_per_second=20,
    save_detected_video=False,
    per_frame_function=on_detect
)
# Turn off the camera
camera.release()
cv2.destroyAllWindows()