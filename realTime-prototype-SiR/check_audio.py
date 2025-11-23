import sounddevice as sd
import numpy as np

def check_devices():
    print(f"--- Available Audio Devices ---")
    print(sd.query_devices())
    
    default_in = sd.query_devices(kind='input')
    default_out = sd.query_devices(kind='output')
    
    print(f"\nDefault Input:  {default_in['name']} (Index: {default_in['index']})")
    print(f"Default Output: {default_out['name']} (Index: {default_out['index']})")
    
    print("\n--- Testing Microphone (3 seconds) ---")
    print("Please speak now...")
    try:
        # Record 3 seconds
        fs = 44100
        recording = sd.rec(int(3 * fs), samplerate=fs, channels=1)
        sd.wait()
        
        amplitude = np.max(np.abs(recording))
        print(f"Max Amplitude detected: {amplitude:.4f}")
        
        if amplitude < 0.01:
            print("❌ WARNING: Microphone signal is dead/silent. Check OS Settings.")
        else:
            print("✅ Microphone detected sound!")
            
        print("\n--- Testing Speakers ---")
        print("Playing back what was recorded...")
        sd.play(recording, fs)
        sd.wait()
        print("✅ Playback finished.")
        
    except Exception as e:
        print(f"❌ Audio Error: {e}")

if __name__ == "__main__":
    check_devices()