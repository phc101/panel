import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import tempfile
import os

# Initialize Mediapipe Pose Detection
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Function to extract frames from video
def extract_frames(video_path, num_frames=5):
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_to_extract = np.linspace(0, frame_count - 1, num_frames, dtype=int)
    
    extracted_frames = []
    for frame_num in frames_to_extract:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            extracted_frames.append(frame_rgb)
    
    cap.release()
    return extracted_frames

# Function to analyze form using Mediapipe
def analyze_form(frames):
    pose = mp_pose.Pose()
    feedback = []
    
    for frame in frames:
        image_rgb = frame.copy()
        results = pose.process(image_rgb)
        
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(image_rgb, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            landmarks = results.pose_landmarks.landmark
            
            # Extract key body angles
            hip_angle = landmarks[mp_pose.PoseLandmark.LEFT_HIP].y - landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y
            knee_angle = landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y - landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y

            # Basic feedback rules
            if hip_angle < 0.1:  # Hips too high
                feedback.append("Your hips are too high. Lower them for better deadlift mechanics.")
            if knee_angle > 0.15:  # Excessive knee bend
                feedback.append("Your knees are bending too much. Engage the hips more.")
        
        feedback.append(image_rgb)  # Store processed frame
    
    pose.close()
    return feedback

# Streamlit UI
st.title("Exercise Form Analysis")
st.write("Upload a video of your exercise, and the system will analyze your form and provide feedback.")

uploaded_video = st.file_uploader("Upload your exercise video", type=["mp4", "mov", "avi"])

if uploaded_video:
    # Save uploaded video temporarily
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())
    video_path = tfile.name

    st.video(video_path)  # Display uploaded video

    st.write("Extracting keyframes...")
    frames = extract_frames(video_path)

    st.write("Analyzing form...")
    feedback = analyze_form(frames)

    # Display feedback
    for item in feedback:
        if isinstance(item, str):
            st.warning(item)
        else:
            st.image(item, caption="Analyzed Frame")

    # Suggest corrective exercises
    st.write("### Suggested Fixes")
    if any("hips too high" in f for f in feedback):
        st.write("- Try the **Squat to Deadlift Position Drill** to lower your hips at setup.")
    if any("knees bending too much" in f for f in feedback):
        st.write("- Focus on **hip engagement** instead of excessive knee flexion.")

st.write("Upload another video after corrections to compare progress!")
