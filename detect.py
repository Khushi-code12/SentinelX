import os
import cv2
from ultralytics import YOLO
import argparse

# For Images Detection
# def detect_images_in_folder(folder_path, model_path, output_folder, conf_threshold=0.25):
#     """
#     Detect objects in all images in a folder using YOLO.

#     Args:
#         folder_path (str): Path to the folder containing images.
#         model_path (str): Path to the YOLO model file (.pt).
#         output_folder (str): Path to save the annotated images.
#         conf_threshold (float): Confidence threshold for detections.
#     """
#     # Load YOLO model
#     model = YOLO(model_path, task="detect")

#     # Create output folder if it doesn't exist
#     os.makedirs(output_folder, exist_ok=True)

#     # Get all image files in the folder
#     image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
#     image_files = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in image_extensions]

#     if not image_files:
#         print("No images found in the folder.")  
#         return

#     print(f"Found {len(image_files)} images in the folder. Processing...")

#     # Process each image
#     for image_file in image_files:
#         image_path = os.path.join(folder_path, image_file)
#         print(f"Processing {image_file}...")

#         # Run YOLO detection
#         results = model(image_path, conf=conf_threshold)

#         # Annotate the image with detections
#         annotated_image = results[0].plot()

#         # Save the annotated image
#         output_path = os.path.join(output_folder, image_file)
#         cv2.imwrite(output_path, annotated_image)
#         print(f"Saved annotated image to {output_path}")

#     print("Processing complete!")

# if __name__ == "__main__":
#     # Define paths and parameters
#     folder_path = "images"  # Replace with the path to your folder
#     model_path = "my_model/my_model.pt"  # Replace with the path to your YOLO model
#     output_folder = "output"  # Replace with the path to save annotated images
#     conf_threshold = 0.5  # Confidence threshold for detections

#     # Run the detection
#     detect_images_in_folder(folder_path, model_path, output_folder, conf_threshold)


def detect_video(input_path, output_path, model_path, conf_threshold=0.25):
    """
    Read a video file or camera stream, run YOLO detection on each frame,
    annotate detections and write to output video.

    Args:
        input_path (str): Path to input video file or integer camera index (e.g. "0").
        output_path (str): Path to save the annotated video.
        model_path (str): Path to the YOLO .pt model file.
        conf_threshold (float): Confidence threshold for detections.
    """
    # Load YOLO model
    model = YOLO(model_path, task="detect")

    # Open video capture
    cap = cv2.VideoCapture(input_path if not input_path.isdigit() else int(input_path))
    if not cap.isOpened():
        print(f"Error: cannot open video {input_path}")
        return

    # Prepare video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Processing {input_path} → {output_path} at {fps:.2f} FPS")
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run detection
        results = model(frame, conf=conf_threshold)
        annotated = results[0].plot()  # draws boxes & labels

        writer.write(annotated)
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx} frames")

    cap.release()
    writer.release()
    print("Done! Annotated video saved.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO video detection & annotation")
    parser.add_argument("--input",  "-i", type=str, required=True,
                        help="Input video path or camera index, e.g. images/videos/01.mp4 or 0")
    parser.add_argument("--output", "-o", type=str, required=True,
                        help="Annotated output video path, e.g. output/01_annotated.mp4")
    parser.add_argument("--model",  "-m", type=str, default="sx_model/my_model.pt",
                        help="Path to the YOLO .pt model (default: sx_model/my_model.pt)")
    parser.add_argument("--conf",   "-c", type=float, default=0.25,
                        help="Confidence threshold (0.0–1.0)")
    args = parser.parse_args()

    detect_video(args.input, args.output, args.model, args.conf)