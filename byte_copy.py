import os

src = r"C:\Users\kumar\.gemini\antigravity\brain\0c348ad3-fdd5-46e1-b79f-2ef66d288f66\media__1773493825458.jpg"
dst = r"c:\Users\kumar\OneDrive\Desktop\Event Planner 2\static\image\corporate_stage.jpg"

try:
    with open(src, 'rb') as f_src:
        content = f_src.read()
        print(f"Read {len(content)} bytes from source.")
        with open(dst, 'wb') as f_dst:
            f_dst.write(content)
            print(f"Wrote {len(content)} bytes to destination.")
    if os.path.exists(dst):
        print(f"VERIFIED: {dst} exists and size is {os.path.getsize(dst)}")
except Exception as e:
    print(f"FAILURE: {e}")
