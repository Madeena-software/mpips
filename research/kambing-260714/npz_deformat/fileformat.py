import numpy as np
import time
import datetime

from commons import log_user_action

def generate_unique_id():
    # Use current epoch time in milliseconds as unique ID
    return str(int(time.time() * 1000))

def epoch_ms_to_datetime(epoch_ms):
    # Convert epoch milliseconds to datetime string
    epoch_sec = int(round(int(epoch_ms) / 1000))
    dt = datetime.datetime.fromtimestamp(epoch_sec)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def xrayparams_to_json(expType, detectorMode, expTime, expEnergy, expCurrent):
    # Convert x-ray parameters to JSON format
    return {
        "expType": expType,
        "detectorMode": detectorMode,
        "expTime": expTime,
        "expEnergy": expEnergy,
        "expCurrent": expCurrent
    }

def cameraparams_to_json(cameraUserID, cameraModel, cameraSerial, pixelType, Exposure, fps, gain):
    # Convert camera parameters to JSON format
    return {
        "cameraUserID": cameraUserID,
        "cameraModel": cameraModel,
        "cameraSerial": cameraSerial,
        "pixelType": pixelType,
        "Exposure": Exposure,
        "fps": fps,
        "gain": gain
    }
epoch_ms = generate_unique_id()
dt_str = epoch_ms_to_datetime(epoch_ms)

def generate_radiograph_file(filename, gainId, darkId, xpar, frameusedcount, campar, darkimg, rawimg, processedimg, description):
    # Generate a radiograph file with the current unique ID
    global unique_id
    unique_id = generate_unique_id()
    try:
        np.savez_compressed(filename,
             id = generate_unique_id(),
             gainid = gainId,
             darkid = darkId,
             xrayparams = xpar,
             frameusedcount = frameusedcount,
             cameraparams = campar,
             darkimage = darkimg,
             rawimage = rawimg,
             processedimage = processedimg,
             description = description
             )
        if xpar["expType"] == "gain":
            log_user_action(f"Gain file '{filename}' generated successfully.")
            print(f"Radiograph file '{filename}' generated successfully.")
        return True
    except Exception as e:
        print(f"Error generating radiograph file: {e}")
        log_user_action(f"Error generating radiograph file '{filename}': {e}")
        return False
    

def load_gain_file(filename):
    try:
        data = np.load(filename, allow_pickle=True)
        return data
    except Exception as e:
        print(f"Error loading gain file: {e}")
        return False

def load_radiograph_file(filename):
    try:
        data = np.load(filename, allow_pickle=True)
        return data
    except Exception as e:
        print(f"Error loading radiograph file: {e}")
        return False