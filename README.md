# SentinelX Crime Reporting System

SentinelX is a sample crime reporting system that leverages a device’s camera (from a phone or laptop) to monitor for potential crime events (for example, mobile theft). When an event is detected, SentinelX records a short video clip capturing the incident and automatically sends an alert (via email, SMS, or webhook) to the designated authority.

## Overview

The goal of SentinelX is to create a modular and extensible system that demonstrates the core concepts of real-time video capture, computer vision–based event detection, and automated alerting. It is intended as a proof-of-concept and educational project, allowing you to experiment with techniques such as motion detection, object recognition, and event buffering.

## Features

- **Real-Time Video Capture:** Continuously captures video from a connected camera.
- **Motion & Object Detection:** Uses techniques like background subtraction (via OpenCV) and pre-trained models (optional deep learning with TensorFlow/PyTorch) to detect unusual movement or potential theft events.
- **Event Buffering:** Automatically records and saves a short video clip (including a few seconds before and after the event) to capture the incident context.
- **Alert Dispatch:** Sends out notifications (email, SMS, or webhook) along with the recorded clip to notify authorities immediately.
- **Modular Design:** Each module (video capture, detection, alerting) is separated for easy modification and future expansion.

## Technologies Used

- **Python 3.10+**
- **OpenCV:** For video capture and image processing.  
- **Deep Learning Frameworks:** TensorFlow or PyTorch for object detection.
- **Flask (Optional):** For creating a web dashboard or handling API endpoints.
- **Alert APIs:** SMTP for email alerts or services like Twilio for SMS notifications.
