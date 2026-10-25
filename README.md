VaaniSync is a powerful AI-driven platform designed to bridge the communication gap by translating spoken language into Indian Sign Language (ISL) in real-time, visualized through a 3D avatar.

## ✨ Key Features

-   **Real-Time Translation:** Ultra-low latency speech-to-sign generation.
-   **High Accuracy:** Utilizes state-of-the-art AI models for transcription and translation.
-   **Cross-Platform:** Seamless experience on Web (React) and Mobile (Flutter).
-   **Offline Mode:** On-device TensorFlow Lite models ensure functionality without an internet connection.
-   **Accessible UI:** Intuitive interface with a clear 3D avatar for sign visualization.

## 🚀 How It Works: The AI Pipeline

Our system operates on an efficient three-stage AI pipeline to deliver fast and accurate results.

1.  **Client-Side Capture:**
    -   Audio is captured on the client device (Web or Mobile).
    -   It's streamed to the backend via **WebSockets** for minimal delay.

2.  **Backend Processing:**
    -   **Stage 1: Transcription:** The audio stream is converted to text using the **Whisper** model.
    -   **Stage 2: Simplification:** The text is processed by a fine-tuned **T5 Transformer** to simplify complex sentences.
    -   **Stage 3: Generation:** A custom-trained model maps the simplified text to corresponding ISL gestures.

3.  **Client-Side Visualization:**
    -   The generated gesture data is sent back to the client.
    -   Our **3D Avatar** renders the signs, completing the translation loop.

## 🛠️ Tech Stack

-   **Frontend:** React (Web), Flutter (Mobile)
-   **Backend:** Python (Flask/FastAPI), WebSockets
-   **AI Models:** Whisper, T5 Transformer, TensorFlow Lite
-   **Database:** [e.g., PostgreSQL, MongoDB - Add your DB if any]
-   **Deployment:** [e.g., Docker, AWS, Vercel - Add your deployment info]

##  Quick Start

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/your-username/vaanisync.git](https://github.com/your-username/vaanisync.git)
    cd vaanisync
    ```

2.  **Install backend dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3.  **Install frontend dependencies:**
    ```sh
    cd frontend
    npm install
    ```

4.  **Run the application:**
    -   Start the backend server.
    -   Start the frontend development server.

## 📄 License

This project is distributed under the MIT License. See `LICENSE` for more information.
