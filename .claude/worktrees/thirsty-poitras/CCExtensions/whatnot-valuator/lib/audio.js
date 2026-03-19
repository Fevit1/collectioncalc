// lib/audio.js - Audio capture and transcription for Whatnot Comic Valuator
// Captures seller audio and extracts grade information

window.ComicAudio = (function() {
  'use strict';

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let audioContext = null;
  let audioStream = null;

  // Initialize audio capture from video element
  async function initAudioCapture() {
    try {
      const video = document.querySelector('video');
      if (!video) {
        console.error('[Audio] No video element found');
        return false;
      }

      // Try to capture audio from the video element
      // Method 1: If video has captureStream
      if (video.captureStream) {
        const stream = video.captureStream();
        const audioTracks = stream.getAudioTracks();
        
        if (audioTracks.length > 0) {
          audioStream = new MediaStream(audioTracks);
          console.log('[Audio] ✅ Captured audio from video stream');
          return true;
        }
      }

      // Method 2: Try mozCaptureStream for Firefox
      if (video.mozCaptureStream) {
        const stream = video.mozCaptureStream();
        const audioTracks = stream.getAudioTracks();
        
        if (audioTracks.length > 0) {
          audioStream = new MediaStream(audioTracks);
          console.log('[Audio] ✅ Captured audio from video stream (moz)');
          return true;
        }
      }

      console.error('[Audio] Could not capture audio from video');
      return false;
    } catch (e) {
      console.error('[Audio] Init error:', e.message);
      return false;
    }
  }

  // Start recording audio
  async function startRecording() {
    if (isRecording) return;

    if (!audioStream) {
      const success = await initAudioCapture();
      if (!success) {
        return { error: 'Could not capture audio. Try refreshing the page.' };
      }
    }

    try {
      audioChunks = [];
      mediaRecorder = new MediaRecorder(audioStream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.start(1000); // Collect in 1-second chunks
      isRecording = true;
      console.log('[Audio] 🎤 Recording started');
      return { success: true };
    } catch (e) {
      console.error('[Audio] Recording error:', e.message);
      return { error: e.message };
    }
  }

  // Stop recording and get audio blob
  async function stopRecording() {
    return new Promise((resolve) => {
      if (!isRecording || !mediaRecorder) {
        resolve({ error: 'Not recording' });
        return;
      }

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        isRecording = false;
        console.log('[Audio] 🛑 Recording stopped, size:', audioBlob.size);
        resolve({ blob: audioBlob, size: audioBlob.size });
      };

      mediaRecorder.stop();
    });
  }

  // Convert blob to base64
  async function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  // Send audio to OpenAI Whisper for transcription
  async function transcribeAudio(audioBlob) {
    // Get OpenAI API key from storage
    const apiKey = await new Promise(resolve => {
      chrome.storage.local.get('openai_api_key', result => {
        resolve(result.openai_api_key || null);
      });
    });

    if (!apiKey) {
      // Fall back to Anthropic for parsing if we have text
      console.log('[Audio] No OpenAI key, cannot transcribe');
      return { error: 'No OpenAI API key. Add one in settings for audio transcription.' };
    }

    try {
      console.log('[Audio] 📤 Sending to Whisper API...');
      
      // Create form data for Whisper API
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.webm');
      formData.append('model', 'whisper-1');
      formData.append('language', 'en');

      const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[Audio] Whisper error:', response.status, errorText);
        return { error: `Transcription failed: ${response.status}` };
      }

      const data = await response.json();
      console.log('[Audio] 📝 Transcription:', data.text);
      return { text: data.text };
    } catch (e) {
      console.error('[Audio] Transcription error:', e.message);
      return { error: e.message };
    }
  }

  // Parse grade from transcribed text
  function parseGradeFromText(text) {
    if (!text) return null;

    const lowerText = text.toLowerCase();
    
    // Direct numeric grades: "9.8", "nine point eight", "9 8", etc.
    const patterns = [
      // Numeric: 9.8, 9.6, etc.
      /\b(\d+\.?\d?)\s*(grade|cgc|cbcs)?\b/gi,
      // "nine eight" or "nine point eight"
      /\b(ten|nine|eight|seven|six|five|four|three|two|one)\s*(point)?\s*(zero|one|two|three|four|five|six|seven|eight|nine)?\b/gi,
      // Grade names
      /\b(mint|near mint|very fine|fine|very good|good|fair|poor)\s*(minus|plus)?\b/gi
    ];

    const wordToNum = {
      'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
      'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    };

    const gradeNameToNum = {
      'mint': 10.0, 'near mint': 9.4, 'near mint minus': 9.2, 'near mint plus': 9.6,
      'very fine': 8.0, 'very fine minus': 7.5, 'very fine plus': 8.5,
      'fine': 6.0, 'fine minus': 5.5, 'fine plus': 6.5,
      'very good': 4.0, 'very good minus': 3.5, 'very good plus': 4.5,
      'good': 2.0, 'good minus': 1.8, 'good plus': 2.5,
      'fair': 1.5, 'poor': 1.0
    };

    // Try to find numeric grade first
    const numericMatch = text.match(/\b(\d+)\.(\d)\b/);
    if (numericMatch) {
      const grade = parseFloat(numericMatch[0]);
      if (grade >= 0.5 && grade <= 10.0) {
        return { grade, raw: numericMatch[0], confidence: 0.9 };
      }
    }

    // Try word numbers: "nine four" = 9.4
    const wordMatch = lowerText.match(/\b(ten|nine|eight|seven|six|five|four|three|two|one)\s*(point)?\s*(zero|one|two|three|four|five|six|seven|eight|nine)?\b/);
    if (wordMatch) {
      const major = wordToNum[wordMatch[1]] || 0;
      const minor = wordMatch[3] ? wordToNum[wordMatch[3]] : 0;
      const grade = major + (minor / 10);
      if (grade >= 0.5 && grade <= 10.0) {
        return { grade, raw: wordMatch[0], confidence: 0.8 };
      }
    }

    // Try grade names
    for (const [name, value] of Object.entries(gradeNameToNum)) {
      if (lowerText.includes(name)) {
        return { grade: value, raw: name, confidence: 0.7 };
      }
    }

    return null;
  }

  // Main listen function - record for N seconds, transcribe, parse
  async function listen(seconds = 8) {
    console.log(`[Audio] 🎤 Listening for ${seconds} seconds...`);
    
    const startResult = await startRecording();
    if (startResult.error) {
      return startResult;
    }

    // Wait for specified duration
    await new Promise(resolve => setTimeout(resolve, seconds * 1000));

    const stopResult = await stopRecording();
    if (stopResult.error) {
      return stopResult;
    }

    // Transcribe
    const transcription = await transcribeAudio(stopResult.blob);
    if (transcription.error) {
      return transcription;
    }

    // Parse grade
    const gradeInfo = parseGradeFromText(transcription.text);

    return {
      text: transcription.text,
      grade: gradeInfo?.grade || null,
      gradeRaw: gradeInfo?.raw || null,
      confidence: gradeInfo?.confidence || 0
    };
  }

  // Save OpenAI API key
  async function saveOpenAIKey(key) {
    return new Promise(resolve => {
      chrome.storage.local.set({ openai_api_key: key }, resolve);
    });
  }

  // Check if OpenAI key exists
  async function hasOpenAIKey() {
    return new Promise(resolve => {
      chrome.storage.local.get('openai_api_key', result => {
        resolve(!!result.openai_api_key);
      });
    });
  }

  return {
    listen,
    startRecording,
    stopRecording,
    parseGradeFromText,
    saveOpenAIKey,
    hasOpenAIKey
  };
})();
