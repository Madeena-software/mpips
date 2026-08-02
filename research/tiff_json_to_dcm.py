import sys
import os
import json
import uuid
import datetime
import cv2
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import UID, ExplicitVRLittleEndian, generate_uid

def tiff_json_to_dcm(tiff_path, json_path, output_path):
    # Load image
    image = cv2.imread(tiff_path, -1)
    if image is None:
        raise ValueError(f"Could not read TIFF image: {tiff_path}")
    imHeight, imWidth = image.shape[:2]
    pixel_bytes = image.tobytes()

    # Load metadata
    with open(json_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    # === FIXED: Generates standard-compliant, purely numeric DICOM UIDs ===
    instanceUID = generate_uid()
    studyUID = generate_uid()
    seriesUID = generate_uid()
    
    # === FIXED: Truncate Accession Number to safe 16-character limit ===
    requestUID = str(uuid.uuid4()).replace('-', '')[:16]

    # File meta info
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = UID('1.2.840.10008.5.1.4.1.1.1.1.1')
    file_meta.MediaStorageSOPInstanceUID = UID(instanceUID)
    file_meta.ImplementationClassUID = UID('1.2.826.0.1.3680043.10.1356.2.1.0.1')
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationVersionName = 'TIFF2DCM_1.0.1'

    ds = FileDataset(output_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.Modality = 'DX'
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = studyUID
    ds.SeriesInstanceUID = seriesUID
    ds.SecondaryCaptureDeviceManufacturer = 'Python'
    ds.StudyDescription = meta.get('StudyDescription', 'Study')
    ds.SeriesDescription = meta.get('SeriesDescription', 'Series')
    ds.InstitutionName = "PT. Madeena Karya Indonesia"
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 0
    
    # === FIXED: Convert floating decimals into string formats for DS VR compliance ===
    scale_x = float(meta.get('Scale X', 1.0)) / 1000.0
    scale_y = float(meta.get('Scale Y', 1.0)) / 1000.0
    # Format to maximum 6 decimal places to prevent exceeding the 16-character limit per value
    ds.PixelSpacing = [f"{scale_x:.6f}", f"{scale_y:.6f}"]
    
    ds.PlanarConfiguration = 0
    ds.HighBit = 15
    ds.BitsStored = 16
    ds.BitsAllocated = 16
    ds.SmallestImagePixelValue = 0
    ds.LargestImagePixelValue = 65535
    ds.WindowCenter = 32768
    ds.WindowWidth = 65536
    ds.Columns = imWidth
    ds.Rows = imHeight
    ds.NumberOfFrames = 1
    ds.PatientName = meta.get('Patient Name', 'Unknown')
    ds.PatientID = meta.get('NIK', 'Unknown')
    
    gender = meta.get('Gender', '').lower()
    if gender == 'male':
        ds.PatientSex = 'M'
    elif gender == 'female':
        ds.PatientSex = 'F'
    else:
        ds.PatientSex = 'O'
        
    # Clean the date by removing hyphens, slashes, or spaces
    raw_birthdate = meta.get('Birthdate', '')
    ds.PatientBirthDate = raw_birthdate.replace('-', '').replace('/', '').strip()

    ds.AccessionNumber = requestUID
    
    # Use Time from JSON if available (YYMMDDhhmmss)
    time_str = meta.get('Time', '').strip()
    if len(time_str) >= 12:
        year = int(time_str[0:2])
        year += 2000 if year < 70 else 1900
        month = int(time_str[2:4])
        day = int(time_str[4:6])
        hour = int(time_str[6:8])
        minute = int(time_str[8:10])
        second = int(time_str[10:12])
        dt = datetime.datetime(year, month, day, hour, minute, second)
        ds.StudyDate = ds.ContentDate = dt.strftime('%Y%m%d')
        ds.StudyTime = ds.ContentTime = dt.strftime('%H%M%S')
    else:
        dt = datetime.datetime.now()
        ds.StudyDate = ds.ContentDate = dt.strftime('%Y%m%d')
        ds.StudyTime = ds.ContentTime = dt.strftime('%H%M%S')
        
    ds.PixelData = pixel_bytes
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    ds.save_as(output_path, write_like_original=False)
    print(f"DICOM file successfully created: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python tiff_json_to_dcm.py <image.tiff> <meta.json> <output.dcm>")
        sys.exit(1)
    tiff_path = sys.argv[1]
    json_path = sys.argv[2]
    output_path = sys.argv[3]
    tiff_json_to_dcm(tiff_path, json_path, output_path)
