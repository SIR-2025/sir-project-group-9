import sounddevice as sd
import numpy as np

def list_and_test():
    print(f"\n--- 1. Listing All Audio Devices ---")
    devices = sd.query_devices()
    print(devices)

    # Automatically try to find a working configuration
    print(f"\n--- 2. Testing Configurations ---")
    
    # Standard rates: 48000 (Hardware), 24000 (OpenAI), 44100 (CD)
    rates = [48000, 24000, 44100] 
    
    # We look for the 'default' or 'pulse' device first, as it handles resampling
    found_input = None
    found_output = None
    
    for idx, device in enumerate(devices):
        name = device['name']
        # Skip HDMI and raw hardware if possible, prefer 'default', 'sysdefault' or 'pulse'
        if "HDMI" in name: 
            continue
            
        print(f"\nChecking Device [{idx}]: {name}")
        
        # Test INPUT
        if device['max_input_channels'] > 0:
            for r in rates:
                try:
                    sd.check_input_settings(device=idx, samplerate=r)
                    print(f"  ✅ Input supported at {r}Hz")
                    if not found_input: found_input = idx
                except Exception:
                    pass
        
        # Test OUTPUT
        if device['max_output_channels'] > 0:
            for r in rates:
                try:
                    sd.check_output_settings(device=idx, samplerate=r)
                    print(f"  ✅ Output supported at {r}Hz")
                    if not found_output: found_output = idx
                except Exception:
                    pass

    print(f"\n--- Recommendation ---")
    print(f"Try setting Input Index: {found_input}")
    print(f"Try setting Output Index: {found_output}")

    # Test Recording with Recommended Settings
    if found_input is not None and found_output is not None:
        print(f"\n--- 3. Testing Audio I/O (Rate: 48000) ---")
        try:
            fs = 48000
            duration = 3  # seconds
            print("Recording 3 seconds (Say something!)...")
            # Force the specific device indices
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, device=(found_input, found_output))
            sd.wait()
            
            print("Playing back...")
            sd.play(recording, fs, device=found_output)
            sd.wait()
            print("✅ Success! Use these indices.")
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    list_and_test()