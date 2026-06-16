const recordBtn = document.getElementById('recordVoiceBtn');
const statusText = document.getElementById('recordingStatus');
const signupForm = document.getElementById('signupForm');
const submitBtn = document.getElementById('submitBtn');

let mediaRecorder = null;
let audioChunks = [];
let voiceBlob = null;

recordBtn.addEventListener('click', async () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        return; // Already recording
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: { echoCancellation: true, noiseSuppression: true } 
        });
        
        let mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/ogg';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = '';
        
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        audioChunks = [];

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            voiceBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
            statusText.textContent = "Voice recorded successfully! ✅";
            recordBtn.textContent = "🎤 Re-record Voice";
            recordBtn.style.background = "rgba(46, 204, 113, 0.2)";
            recordBtn.style.borderColor = "#2ecc71";
            
            // Stop mic tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        recordBtn.textContent = "Recording... (speak for 5s)";
        statusText.textContent = "Listening...";
        
        // Record for exactly 5 seconds
        setTimeout(() => {
            if (mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
        }, 5000);

    } catch (err) {
        console.error("Mic error:", err);
        statusText.textContent = "Microphone access denied.";
    }
});

// Intercept form submit to append audio file
signupForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    if (!voiceBlob) {
        statusText.textContent = "⚠️ Please record your voice first!";
        statusText.style.color = "#ff4757";
        return;
    }

    submitBtn.textContent = "Creating Account...";
    submitBtn.disabled = true;

    const formData = new FormData(signupForm);
    formData.append("voice_sample", voiceBlob, "enrollment.webm");

    fetch('/signup', {
        method: 'POST',
        body: formData
    })
    .then(res => {
        if (res.redirected) {
            window.location.href = res.url;
        } else {
            return res.text();
        }
    })
    .then(html => {
        if (html) {
            // Re-render the page with the error
            document.open();
            document.write(html);
            document.close();
        }
    })
    .catch(err => {
        console.error("Signup error:", err);
        submitBtn.textContent = "Sign Up";
        submitBtn.disabled = false;
    });
});
