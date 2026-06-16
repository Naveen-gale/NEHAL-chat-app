// --- DOM ELEMENTS ---
const avatarContainer = document.getElementById('avatarContainer');
const avatar = document.getElementById('avatar');
const userTranscript = document.getElementById('userTranscript');
const aiTranscript = document.getElementById('aiTranscript');
const fallbackInputContainer = document.getElementById('fallbackInputContainer');
const fallbackInput = document.getElementById('fallbackInput');
const fallbackSendBtn = document.getElementById('fallbackSendBtn');
const endCallBtn = document.querySelector('.end-call-btn');
const liveCopyBtn = document.getElementById('liveCopyBtn');

if (liveCopyBtn) {
    liveCopyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(aiTranscript.textContent).then(() => {
            const old = liveCopyBtn.textContent;
            liveCopyBtn.textContent = "✅ Copied";
            setTimeout(() => liveCopyBtn.textContent = old, 2000);
        });
    });
}

let mediaRecorder = null;
let audioChunks = [];
let isSessionActive = false; 
let isRecording = false;     
let isAiSpeaking = false;    
let audioPlayback = null;    
let micStream = null;        

// Web Audio API variables
let audioContext = null;
let analyser = null;
let micSource = null;
let silenceTimer = null;
let maxRecordingTimer = null; 
let isUserSpeaking = false;
let animationFrameId = null;

// FIX 1: Lowered threshold massively so even quiet talking triggers it
const SILENCE_THRESHOLD = 0.003; 
const SILENCE_DELAY = 250;      

function setAvatarState(state) {
    avatar.className = 'avatar ' + state;
}

function showFallbackInput() {
    if (fallbackInputContainer) {
        fallbackInputContainer.style.display = 'block';
    }
}

// 🎤 START/STOP LIVE HANDS-FREE SESSION
async function startSession() {
    isSessionActive = true;
    setAvatarState('idle');
    userTranscript.textContent = "Connecting...";
    aiTranscript.textContent = "Starting secure audio channel...";
    
    startRecordingLoop();
}

function endSession() {
    isSessionActive = false;
    setAvatarState('idle');
    userTranscript.textContent = "Call Ended.";
    aiTranscript.textContent = "Click the avatar to restart.";
    
    cleanupMic();
    
    if (audioPlayback) {
        audioPlayback.pause();
        audioPlayback = null;
    }
    isAiSpeaking = false;
}

// Wire up the Avatar and End Call button
if (avatarContainer) {
    avatarContainer.addEventListener('click', () => {
        if (isSessionActive) endSession();
        else startSession();
    });
    avatarContainer.style.cursor = 'pointer'; 
}

if (endCallBtn) {
    endCallBtn.addEventListener('click', (e) => {
        if(isSessionActive) {
            e.preventDefault(); 
            endSession();
        }
    });
}

// 🔄 HANDS-FREE RECORDING LOOP
async function startRecordingLoop() {
    if (!isSessionActive) return;
    
    audioChunks = [];
    isUserSpeaking = false;
    
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        });
        
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }
        
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        micSource = audioContext.createMediaStreamSource(micStream);
        
        // FIX 2: Removed the High-Pass Filter. Connecting microphone directly to the analyzer.
        micSource.connect(analyser);
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        // Setup MediaRecorder
        let mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/ogg';
        if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = ''; 
        
        mediaRecorder = new MediaRecorder(micStream, { mimeType });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };
        
        mediaRecorder.onstart = () => {
            isRecording = true;
            setAvatarState('listening');
            userTranscript.textContent = "Listening... (speak now)";
            aiTranscript.textContent = "";
        };
        
        mediaRecorder.onstop = () => {
            isRecording = false;
            
            if (!isSessionActive) return;
            
            // ALWAYS send audio to backend - let Whisper decide if there's speech
            const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
            
            if (audioBlob.size < 1000) {
                // Too tiny to contain speech, restart
                console.log("Audio blob too small, restarting...");
                cleanupMic();
                if (isSessionActive) startRecordingLoop();
                return;
            }
            
            console.log("Sending audio to backend, size:", audioBlob.size);
            sendAudioToBackend(audioBlob);
            cleanupMic(); 
        };
        
        // Monitor Volume & Detect Silence
        function monitorVolume() {
            if (!isRecording || !isSessionActive) return;
            
            analyser.getByteTimeDomainData(dataArray);
            
            let total = 0;
            for (let i = 0; i < bufferLength; i++) {
                const val = (dataArray[i] - 128) / 128; 
                total += val * val;
            }
            const rms = Math.sqrt(total / bufferLength);
            
            // Debug line: You can look in the console to see EXACTLY what volume your browser hears
            // console.log("Current Mic RMS:", rms.toFixed(5));
            
            // Scale avatar slightly with loud noises
            if (rms > 0.015) {
                avatar.style.transform = `scale(${1 + rms * 0.3})`;
            } else {
                avatar.style.transform = 'scale(1)';
            }
            
            if (rms > SILENCE_THRESHOLD) {
                isUserSpeaking = true;
                if (silenceTimer) {
                    clearTimeout(silenceTimer);
                    silenceTimer = null;
                }
            } else {
                if (!silenceTimer) {
                    const delay = isUserSpeaking ? SILENCE_DELAY : 5000;
                    silenceTimer = setTimeout(() => {
                        stopRecording();
                    }, delay);
                }
            }
            
            animationFrameId = requestAnimationFrame(monitorVolume);
        }
        
        mediaRecorder.start();
        monitorVolume();
        
        maxRecordingTimer = setTimeout(() => {
            stopRecording();
        }, 15000);
        
    } catch (err) {
        console.error("Microphone error:", err);
        endSession();
        userTranscript.textContent = "⚠️ Mic access denied.";
        showFallbackInput();
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
}

function cleanupMic() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (silenceTimer) clearTimeout(silenceTimer);
    if (maxRecordingTimer) clearTimeout(maxRecordingTimer);
    
    if (micStream) {
        micStream.getTracks().forEach(track => track.stop());
        micStream = null;
    }
    if (audioContext) {
        audioContext.close().catch(() => {});
        audioContext = null;
    }
    avatar.style.transform = 'scale(1)';
}

// 📤 BACKEND INTEGRATION
function sendAudioToBackend(audioBlob) {
    setAvatarState('thinking'); 
    aiTranscript.textContent = "Processing...";
    if (liveCopyBtn) liveCopyBtn.classList.add("hidden");
    
    const formData = new FormData();
    formData.append("audio", audioBlob, "voice.webm");

    fetch("/chat_voice", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        // Backend says no speech was found, silently restart
        if (data.retry) {
            console.log("No speech detected by Whisper, restarting...");
            setAvatarState('idle');
            if (isSessionActive) startRecordingLoop();
            return;
        }
        
        if (data.error) {
            userTranscript.textContent = `⚠️ Error: Could not understand audio.`;
            aiTranscript.textContent = "";
            setAvatarState('idle');
            setTimeout(() => {
                if (isSessionActive) startRecordingLoop();
            }, 2000);
            return;
        }

        userTranscript.textContent = data.user_text;
        
        if (data.requires_login) {
            aiTranscript.innerHTML = `Redirecting to Sign Up...`;
            setAvatarState('idle');
            setTimeout(() => {
                window.location.href = '/signup';
            }, 1500);
            endSession(); 
        } else {
            aiTranscript.textContent = data.reply;
            if (liveCopyBtn) liveCopyBtn.classList.remove("hidden");
        }

        if (data.audio_url) {
            playAudio(data.audio_url);
        } else if (data.reply) {
            setAvatarState('idle');
            if (isSessionActive) startRecordingLoop();
        } else {
            setAvatarState('idle');
            if (isSessionActive) startRecordingLoop();
        }
    })
    .catch(err => {
        console.error("Fetch error:", err);
        aiTranscript.textContent = "Server connection lost.";
        endSession();
    });
}

function playAudio(audioUrl) {
    if (audioPlayback) {
        audioPlayback.pause();
    }
    
    audioPlayback = new Audio(audioUrl);
    
    audioPlayback.onplay = () => {
        isAiSpeaking = true;
        setAvatarState('speaking');
    };
    
    audioPlayback.onended = () => {
        isAiSpeaking = false;
        setAvatarState('idle');
        if (isSessionActive) startRecordingLoop();
    };
    
    audioPlayback.onerror = () => {
        console.error("Audio playback error");
        isAiSpeaking = false;
        setAvatarState('idle');
        if (isSessionActive) startRecordingLoop();
    };
    
    audioPlayback.play().catch(e => {
        console.error("Playback prevented:", e);
        isAiSpeaking = false;
        setAvatarState('idle');
        if (isSessionActive) startRecordingLoop();
    });
}

// ⌨️ FALLBACK TYPING MECHANISM
function sendFallbackMessage() {
    const text = fallbackInput.value.trim();
    if (!text) return;
    
    cleanupMic();
    if (audioPlayback) {
        audioPlayback.pause();
        audioPlayback = null;
    }
    isAiSpeaking = false;
    
    userTranscript.textContent = text;
    fallbackInput.value = '';
    
    setAvatarState('thinking');
    aiTranscript.textContent = "";
    if (liveCopyBtn) liveCopyBtn.classList.add("hidden");

    const formData = new FormData();
    formData.append("text", text);

    fetch("/chat_voice", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            aiTranscript.textContent = "Unable to get response.";
            setAvatarState('idle');
            return;
        }
        
        if (data.requires_login) {
            aiTranscript.innerHTML = `Redirecting to Sign Up...`;
            setTimeout(() => {
                window.location.href = '/signup';
            }, 1500);
            endSession();
        } else {
            aiTranscript.textContent = data.reply;
            if (liveCopyBtn) liveCopyBtn.classList.remove("hidden");
        }

        if (data.audio_url) {
            playAudio(data.audio_url);
        } else if (data.reply) {
            setAvatarState('idle');
            if (isSessionActive) startRecordingLoop();
        } else {
            setAvatarState('idle');
            if (isSessionActive) startRecordingLoop();
        }
    })
    .catch(() => {
        aiTranscript.textContent = "Server connection lost.";
        setAvatarState('idle');
    });
}

if (fallbackSendBtn) {
    fallbackSendBtn.addEventListener('click', sendFallbackMessage);
}
if (fallbackInput) {
    fallbackInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') sendFallbackMessage();
    });
}

// INIT UI
updateAuthUI();

function updateAuthUI() {
    fetch("/auth_status")
    .then(res => res.json())
    .then(data => {
        const userBadge = document.getElementById("userBadge");
        if (!userBadge) return;
        if (data.is_registered) {
            userBadge.textContent = `${data.username}`;
            userBadge.style.color = "#ec4899";
        } else {
            userBadge.textContent = "Guest";
        }
    }).catch(()=>{});
}

// Startup Logic Check
if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showFallbackInput();
} else {
    userTranscript.textContent = "Ready.";
    aiTranscript.textContent = "Click the glowing orb to start the call.";
}