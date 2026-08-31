"""Bounded, read-only BED threshold-policy characterization."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from mpips.iqa import analyze_structural_preservation
from mpips.pipelines.config import ImagerPipelineConfig
from mpips.pipelines.radiography import RadiographyPipeline
import mpips.pipelines.radiography as radiography_module
from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_radiograph,
    sha256_file,
    to_uint16,
)

SOURCE_FOLDER = (
    "https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8"
)
COHORT_CAP = 12
GAIN_URLS = {
    "Ambil Data 1": "https://drive.google.com/file/d/1i9nT2bQ3VG3_TfAGHNpQDVi50JAC2Cyq/view",  # noqa: E501
    "Ambil Data 2": "https://drive.google.com/file/d/1Y3-dD4k2a_SRvfCC7Ezyj-v9ImColQjK/view",  # noqa: E501
    "Ambil Data 3": "https://drive.google.com/file/d/1nGjmoE0cGxT5lU-7KnMJG1-51N34w0Wo/view",  # noqa: E501
    "Ambil Data 4": "https://drive.google.com/file/d/1HeuhINTVSA7tyNBBi4rSZeOdDbAmR6ds/view",  # noqa: E501
    "Ambil Data 5": "https://drive.google.com/file/d/1S--NR9uk6vK11nqgT1WAzHWMqGg3vasc/view",  # noqa: E501
    "Ambil Data 6": "https://drive.google.com/file/d/1R6o53hMVBy3B__cAqJBUhwcoTn14VGWF/view",  # noqa: E501
}

# Inventory was frozen from the authorized Drive folder before processing.
CANDIDATES = [
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782704291612.npz",
        "1AUS04DQYHorVUBc1JVvyay7loDC3tDGG",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782704291612.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782704496787.npz",
        "175v1A7y3ixN-9so3O_oTKRLSmvo1HdeY",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782704496787.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782704609899.npz",
        "1W8kwxTu8TVHD_F8iMC1b4Hqz09tI2s3b",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782704609899.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782704876145.npz",
        "13-TCIVD5dYyNMcgk3Y82OCKh2oyAGVkF",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782704876145.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782705024307.npz",
        "1pF79xYv8qjkaZZq6xBLYZ6Gfj-eftVXY",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782705024307.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782705542759.npz",
        "11-1K-JAzsslLHxsgxrICiBM1pjRpXtpq",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782705542759.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782705825057.npz",
        "1qsZoM2H1zqeE2UGUQIOFWOrIZewy68vQ",
        "Ambil Data 1/file npz/kambing-1/Copy of BED_1782705825057.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782706308504.npz",
        "1VO11y9c0D-6R3fzWFVSjcJzwvDqWENcw",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782706308504.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782706389577.npz",
        "16N8Ca49q2CuaGngbHyY81wbh-JP5JKH9",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782706389577.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782706462669.npz",
        "13xCB_KTbusYGPXRCIVc4R7Nc2J9LgJTu",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782706462669.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782706601776.npz",
        "1rwmJCNWUY_sTQlh0zjP6hvf4Pa99YgHQ",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782706601776.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782707209358.npz",
        "1dl7byx0pxbT6JxWRVPM49i13oGaiVhK7",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782707209358.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782707391521.npz",
        "1mliaczOku_e_5SztHc7ZOdPNWrYE4tIp",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782707391521.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782707631749.npz",
        "1s5TTQWFXro1lgb1cnHq-dlOiw_9kGaUW",
        "Ambil Data 1/file npz/kambing-2/Copy of BED_1782707631749.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708151260.npz",
        "18ZkmCLe0fpoGIHL4Nday4dhqlTnkvgeF",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708151260.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708239353.npz",
        "1sVSB-rGyeWM8ODxTtATUxvz-Idtd6CfR",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708239353.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708316414.npz",
        "1kfKVJEpmRszmHtFlKk6il8Hb603ywwwk",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708316414.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708418534.npz",
        "17wDF0tcmYiBKX1Qxw1Q6ltkLXFF-oaY3",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708418534.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708510607.npz",
        "1bVMOhwdJ7b1SNQOnXcrP2RFURdcNRBbR",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708510607.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708633721.npz",
        "1BkEo7gSCKJCOOs10CtChD5MeEznn0O4p",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708633721.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708771849.npz",
        "1UjnZTk-xu7f5k0G6ebdG2p71bGchK_6V",
        "Ambil Data 1/file npz/kambing-3/Copy of BED_1782708771849.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709216265.npz",
        "1nYWfdk_Ud6ZmMBB4NOWDNKHkPvXBmIim",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709216265.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709292323.npz",
        "1LcFIcoN7AkzODG506gDb8yozarHHvbL4",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709292323.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709369407.npz",
        "1Ecz4dZSgeE1_DpGlu5pLmj2OzV1hmjn_",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709369407.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709478478.npz",
        "15dlB7o8yHHXMCJ6GNWcYF_xcE1yr1nB7",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709478478.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709567557.npz",
        "1oKESTSJmMQJXw0Z9oI_eWNXnZ3rNMQVY",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709567557.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709720714.npz",
        "1Z4OWqjDBPgMRJtGkr5_9XtkXm6ZMbzm4",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709720714.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-4",
        "Copy of BED_1782709837825.npz",
        "1lYUkas38ydKsBweXVxx9orUujygRE6NC",
        "Ambil Data 1/file npz/kambing-4/Copy of BED_1782709837825.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710431424.npz",
        "1rHK4DAQkmW-pl-Z2CvthKc9BziYYNRRa",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710431424.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710499459.npz",
        "15IwzB8GQbj29fly9T9a_7YYi4IHPloTr",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710499459.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710570525.npz",
        "1t8TFzC6Kf-H9B6gJMVnLHXEWJ5w6v9Vc",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710570525.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710660602.npz",
        "15j-_tMmGqgbDXFgGkRKHVq9AQIPSFn0d",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710660602.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710730670.npz",
        "1vWjIVj5gMG7zH9XbjAf53wi0qmvFnYqK",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710730670.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710863808.npz",
        "1OtlvLqPpHE1j3W4kYoNN2efsjQmLAFt-",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710863808.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-5",
        "Copy of BED_1782710986916.npz",
        "1sBJ-m5V9y_lVLJbZwpXUL5Hp2YokOX7U",
        "Ambil Data 1/file npz/kambing-5/Copy of BED_1782710986916.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782711579481.npz",
        "14zlqIJhb-QdSZ8RgfkoQlOHgufsmAsmp",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782711579481.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782711843728.npz",
        "1vbMxpcsWSGoaiKT2njssBBMROCC6rKrW",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782711843728.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782711917810.npz",
        "1csy5MsjaVUsg2AlZYJWrjFQCWtX6E2cg",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782711917810.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782712025913.npz",
        "1bwhU-5UUYrUOs0cGOC0XSDCxvDHAs3wC",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782712025913.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782712090948.npz",
        "1S3-TsIwVN3vY5osTpOH5lHSxoDfVOyVI",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782712090948.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782712218078.npz",
        "142dCQ9OkkaXKpjklgTkljk2lBseBgi0Z",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782712218078.npz",
    ),
    (
        "Ambil Data 1",
        "kambing-6",
        "Copy of BED_1782712355221.npz",
        "1Nxba4R7JCb26HH_E1qMWqSlIiyL9roZz",
        "Ambil Data 1/file npz/kambing-6/Copy of BED_1782712355221.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222264263.npz",
        "1sLur8whVT8Vb4OJeVIduSJFBQ3wKCOVX",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222264263.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222354297.npz",
        "1tZJDoZ5L-7zS_gmOQkNb6mPwFSgyN5L2",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222354297.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222443425.npz",
        "1LLVflPIZPqP0W_88cENbIz1ECgb3zABH",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222443425.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222540490.npz",
        "1Yl0urTRpP0A0ezIolhVfAOMhPmdVbqin",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222540490.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222656603.npz",
        "1zHJGP_sqC-3Rt0jQPSUFiI85TtYn14xp",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222656603.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222840758.npz",
        "1jVaH36g02dnkNU9sYRBa8P5Lbst5Nnz3",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222840758.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222981898.npz",
        "1MVLXqgF6tDStIEhrDn0Ec6HOJxnA_eAP",
        "Ambil Data 2/npz file/kambing-1/Copy of BED_1783222981898.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223476352.npz",
        "1NoKEdKmB3UsuIYA7GogLfqa2AEkS2cTE",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223476352.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223562469.npz",
        "1vzOF3cGQY1DjiD0bbTg9tkHIUgjkMw5S",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223562469.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223634515.npz",
        "12oFFcO1d9ZeqEksDhHDrELFKB7K6Sg2I",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223634515.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223746618.npz",
        "1APTWR9Iwr6M_XTXFk1OxWDXMQDqawDnA",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223746618.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223821669.npz",
        "1oi-OlOhdOlGWlAUgVNQDbf_eY3jPCUFg",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223821669.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223971814.npz",
        "14ZzNOF0b2g83Nh7EAGreERhvaVnA5nqs",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783223971814.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783224123973.npz",
        "13fLNu82aaHfTQmuP5gzFmWI3Mn78Vbu8",
        "Ambil Data 2/npz file/kambing-2/Copy of BED_1783224123973.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783224645493.npz",
        "10TLqDtRzvcyOR8eqpYpGtcj3PFh5Njwn",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783224645493.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783224779601.npz",
        "1jdYBl8GKxadJ5zM5wL77VKQSww8BZbE0",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783224779601.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783224845666.npz",
        "15sIj6J-ObWAjAE9GBqCjrKZHZrbj8_qk",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783224845666.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783224949762.npz",
        "1UbZCrfK-5koXQ2vCreuf0cxm9MnTi-8e",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783224949762.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783225038829.npz",
        "12hqEvkTPXFsNB77QvKPZ1UCmIl3ZlTUB",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783225038829.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783225171982.npz",
        "1l9inehhc0lSCgDuDzlQqlGXaAq4G1l0J",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783225171982.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783225312099.npz",
        "1wa-WwYOQpL-ztBmA2geGn2FUc50trQne",
        "Ambil Data 2/npz file/kambing-3/Copy of BED_1783225312099.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783225778535.npz",
        "1wUnpGzBAGs4Ie1AnNMnZM86bYsW49Kwa",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783225778535.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783225856630.npz",
        "1wc4n1453zu36Rrsu13xBtPjMxOGlkkQe",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783225856630.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783225925658.npz",
        "13vEMFOyerZG-KLkzQ_aG5OVnGOzBs4Ur",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783225925658.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783226005775.npz",
        "1sVZLd-llhT3-qUNyvGxZeLem20tgVK-v",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783226005775.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783226094822.npz",
        "1wA7mUqGTuqMdow58WUlC_gywrKjX5030",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783226094822.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783226292060.npz",
        "1k02-Ep_sog-EWnmylkDVYqS0HIdCQA7n",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783226292060.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-4",
        "Copy of BED_1783226438224.npz",
        "17706l763qWc8YBm2P6BdRcGq4TI2ltPm",
        "Ambil Data 2/npz file/kambing-4/Copy of BED_1783226438224.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783226837535.npz",
        "1JEZSgXpNYO8vSpNz-kTjUy0QJjKO_WEl",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783226837535.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783226943629.npz",
        "1uLbqftTAIrlC8y0h7lYemkEJPrlADZ3Z",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783226943629.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783227041737.npz",
        "1dFrX9JtuyXN3QoXU4L1-r2-0LFsuD-E2",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783227041737.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783227145828.npz",
        "1VALsGI7CRw_-zQXjZKwbrKIQZDTOEibg",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783227145828.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783227214908.npz",
        "10u1Us1ab-dT4TUuiQ_ecAnhlzQhlsZ1k",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783227214908.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783227322021.npz",
        "1Yscs9kG2xjAZyUscPe5pJNl3E3KkxcYw",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783227322021.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-5",
        "Copy of BED_1783227455147.npz",
        "1di_opXCC9iAkaL5EJ7lOYTtS5sdWe3CR",
        "Ambil Data 2/npz file/kambing-5/Copy of BED_1783227455147.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783227764453.npz",
        "1DRg01Xiicp-JzJMwq0fn4tTmr9_1N4Ev",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783227764453.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783227855534.npz",
        "13I8I7rQOgybfUOoTfFOm09V-PBJ_7SIY",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783227855534.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783227937635.npz",
        "13s_oDNhbXJ7w0LUoR_Sm84clowMP5Kdf",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783227937635.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783228015668.npz",
        "13ZRCHjKaYfiuF13DjdG_J8Emg0L27o-6",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783228015668.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783228084756.npz",
        "1UE3qe7Zil6lKGLwkBFLzWBditaXNruyW",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783228084756.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783228204857.npz",
        "1OegjFylNu6uXO8eLo43AjWGCKn1WLuCi",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783228204857.npz",
    ),
    (
        "Ambil Data 2",
        "kambing-6",
        "Copy of BED_1783228340962.npz",
        "1o0CElGORcOsOwYaRPKbUn7zG3wjAlhhI",
        "Ambil Data 2/npz file/kambing-6/Copy of BED_1783228340962.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783826993793.npz",
        "1PUF1XhPkGBMPdh8CMXjrEh9-yW6go3a3",
        "Ambil Data 3/npz file/kambing 1/BED_1783826993793.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827067828.npz",
        "1QWnZSu_9CP1TuVVfbjQtscAylj25N-Ol",
        "Ambil Data 3/npz file/kambing 1/BED_1783827067828.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827140872.npz",
        "16MNB3mL4p4_t7YM_fAFEPub3xDGxde7q",
        "Ambil Data 3/npz file/kambing 1/BED_1783827140872.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827329050.npz",
        "100_QUPOVaXhSwMt_3Z3bOzUHD6Gs6dtB",
        "Ambil Data 3/npz file/kambing 1/BED_1783827329050.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827672400.npz",
        "14tg1YiPbFF9UKFAmnE4Ey2FnHSzuQqkz",
        "Ambil Data 3/npz file/kambing 1/BED_1783827672400.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827839548.npz",
        "1IDf_aRKWB33SwL6C0K236hmJOod6HgFS",
        "Ambil Data 3/npz file/kambing 1/BED_1783827839548.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827970684.npz",
        "1ySegpyhWMr0I_Vf6qirFxPdnsCQ3Q_o7",
        "Ambil Data 3/npz file/kambing 1/BED_1783827970684.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828512202.npz",
        "1lYm_xd-M-p5cjkBO7GthsKG-anY_ZLVX",
        "Ambil Data 3/npz file/kambing 2/BED_1783828512202.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828578230.npz",
        "1-N14Ft1bFnnszstCTTMXX4JrnYXK2FWu",
        "Ambil Data 3/npz file/kambing 2/BED_1783828578230.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828646305.npz",
        "1UijNvbJACKbhUqqW7UAO4nFHGPFJxLwH",
        "Ambil Data 3/npz file/kambing 2/BED_1783828646305.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828775434.npz",
        "1E-k9eql4_puC0xVfnkfVntA7eXaZduK8",
        "Ambil Data 3/npz file/kambing 2/BED_1783828775434.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828930578.npz",
        "1Z8HV7F5TMghrmKKtW7wjtetc7Uy9Crtf",
        "Ambil Data 3/npz file/kambing 2/BED_1783828930578.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783829069740.npz",
        "1MiHQpkD57MwQUP5gIeTRaWhbQgdTYpyU",
        "Ambil Data 3/npz file/kambing 2/BED_1783829069740.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783829195829.npz",
        "1ZfSwYvI92g_Ls_w-Nn2wRsKJBgbcooiv",
        "Ambil Data 3/npz file/kambing 2/BED_1783829195829.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829675331.npz",
        "1VRfv9srolhOXDYoLIKWOkBpM2yFbLe-h",
        "Ambil Data 3/npz file/kambing 3/BED_1783829675331.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829741377.npz",
        "1WUZK2n5TWfQ4KzVs6qut5gS6ASzM3U-_",
        "Ambil Data 3/npz file/kambing 3/BED_1783829741377.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829810421.npz",
        "12MZpQJn_pnVV32AeDgfldR68Ft4GGd67",
        "Ambil Data 3/npz file/kambing 3/BED_1783829810421.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829900514.npz",
        "1CFUnzrfAGyyyJni7Gy0jXQUIvwomS6sw",
        "Ambil Data 3/npz file/kambing 3/BED_1783829900514.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829993622.npz",
        "1nk3zyIc1ekTx4AP7JX4jKzjV37b0NpvR",
        "Ambil Data 3/npz file/kambing 3/BED_1783829993622.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783830162772.npz",
        "1hWVS3nyuzm7QnGGN8E7d3lKkXBirPpx3",
        "Ambil Data 3/npz file/kambing 3/BED_1783830162772.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783830282868.npz",
        "1RbAvdVdqQCSyEaDa7rXyxbsAXarp1aoJ",
        "Ambil Data 3/npz file/kambing 3/BED_1783830282868.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783830710271.npz",
        "1oXy6QVnQg3HM5UOSw2OOvZp4bBB290Yx",
        "Ambil Data 3/npz file/kambing 6/BED_1783830710271.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783830782332.npz",
        "1c99v5OI5tg6ABOXZulTRu8u-5VsA3unG",
        "Ambil Data 3/npz file/kambing 6/BED_1783830782332.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783830852420.npz",
        "1xxO4d8TwqNR_pXSAyo2wT1NgKP9KtWjp",
        "Ambil Data 3/npz file/kambing 6/BED_1783830852420.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783830950499.npz",
        "1dLXZuCkDpnHda4oJDAbug3JBlJknYDk0",
        "Ambil Data 3/npz file/kambing 6/BED_1783830950499.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783831074610.npz",
        "1OKQ3sP7mqAb53dKJZj-uZ6xMW38E0uBW",
        "Ambil Data 3/npz file/kambing 6/BED_1783831074610.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783831206802.npz",
        "1StSOfCtEOKSE9vm52J69wfx8mY4TQI_6",
        "Ambil Data 3/npz file/kambing 6/BED_1783831206802.npz",
    ),
    (
        "Ambil Data 3",
        "kambing 6",
        "BED_1783831327881.npz",
        "1grAQTcExm05ahuXmSj6FtR29sg8rOFLQ",
        "Ambil Data 3/npz file/kambing 6/BED_1783831327881.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784431721478.npz",
        "1AGDbZmXqGBDeftQMX7jk5MBl0bCTckVm",
        "Ambil Data 4/npz file/kambing 1/BED_1784431721478.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784431803611.npz",
        "1hTIa3PMN1fHWVXSkROjYrPjZz0THw3yy",
        "Ambil Data 4/npz file/kambing 1/BED_1784431803611.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784431878624.npz",
        "1zRstW1fjkydKTN6x53lr-rLaMV9w9g1r",
        "Ambil Data 4/npz file/kambing 1/BED_1784431878624.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784431973728.npz",
        "1QaeTHr5Mqz70thUewa8nIqt5qgzdTGAo",
        "Ambil Data 4/npz file/kambing 1/BED_1784431973728.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784432134867.npz",
        "1M-LlGNQ3uuRoGV1hcAlxvGHsk2fcwc8q",
        "Ambil Data 4/npz file/kambing 1/BED_1784432134867.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784432255973.npz",
        "1uVcpCuiROWLcYfel4iNSjGh8xLwj7g8i",
        "Ambil Data 4/npz file/kambing 1/BED_1784432255973.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 1",
        "BED_1784432527218.npz",
        "1386to8CGxIdluuN8W5iMikFZ9tQkLEjP",
        "Ambil Data 4/npz file/kambing 1/BED_1784432527218.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433110774.npz",
        "1ns4-MEAy0OPP49BHQ_WAn2mjk-0ThK5c",
        "Ambil Data 4/npz file/kambing 2/BED_1784433110774.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433180826.npz",
        "16HSV0YgdllwuPD4Bgb5KB8UYe0tfJ-kj",
        "Ambil Data 4/npz file/kambing 2/BED_1784433180826.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433250888.npz",
        "1pbgmo6NXt1r4NYJOsgJB9hoUSxu17Id8",
        "Ambil Data 4/npz file/kambing 2/BED_1784433250888.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433339985.npz",
        "1qDP8BNSI7uMGWrkGgwBqKDhSnhTP3j4H",
        "Ambil Data 4/npz file/kambing 2/BED_1784433339985.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433450076.npz",
        "1npm6ZAr_MTT0a8FqbfqUaplhSkyaHeso",
        "Ambil Data 4/npz file/kambing 2/BED_1784433450076.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433561171.npz",
        "16GdkZvrkrJY6bfFJU540vszal3gOglU4",
        "Ambil Data 4/npz file/kambing 2/BED_1784433561171.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 2",
        "BED_1784433773391.npz",
        "1OmLUpG5uGjiMZASPO1zZalfXy96e0HVC",
        "Ambil Data 4/npz file/kambing 2/BED_1784433773391.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434125723.npz",
        "1SXOn170QCoSobVJmUjc7OKkaG4hUl-aj",
        "Ambil Data 4/npz file/kambing 3/BED_1784434125723.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434192888.npz",
        "19bXizgv7tc3DeyT8JVkDBn-Iu7O8Yrzv",
        "Ambil Data 4/npz file/kambing 3/BED_1784434192888.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434267893.npz",
        "19VbClwpNysW8q5vOPM7o38IXaUACvm8T",
        "Ambil Data 4/npz file/kambing 3/BED_1784434267893.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434376957.npz",
        "1tEps6-8ltWcPTcaCXsX6Xnlo0OJD6D_L",
        "Ambil Data 4/npz file/kambing 3/BED_1784434376957.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434485111.npz",
        "1-yBooZgbxTWGnjCsbnsL8p5WUbqUPyEG",
        "Ambil Data 4/npz file/kambing 3/BED_1784434485111.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434586213.npz",
        "1-0b405sqevI6JC0Xl5NkgsI_IoNSBmVs",
        "Ambil Data 4/npz file/kambing 3/BED_1784434586213.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 3",
        "BED_1784434688261.npz",
        "1yEKhE3JqsmQ3C5ovqmuNP4oChHd_XzTy",
        "Ambil Data 4/npz file/kambing 3/BED_1784434688261.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435083633.npz",
        "1jLdXZ9Iv7n0jGCxTJpr5Xeku9mgq2dNp",
        "Ambil Data 4/npz file/kambing 6/BED_1784435083633.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435153737.npz",
        "1AHl7rNZ5SIGfELD-R0rTghjh2gxSLQ2s",
        "Ambil Data 4/npz file/kambing 6/BED_1784435153737.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435220783.npz",
        "1Kt3qwetz2omrimYGxZRNUGW9Yb4R9XVY",
        "Ambil Data 4/npz file/kambing 6/BED_1784435220783.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435315850.npz",
        "1A4uPYAI-5egqwPMNpz9vLsbF45Qz3dxq",
        "Ambil Data 4/npz file/kambing 6/BED_1784435315850.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435393933.npz",
        "1w5a0ZV2T3HD-7fvxDI4W7kw0pa7Kned9",
        "Ambil Data 4/npz file/kambing 6/BED_1784435393933.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435517059.npz",
        "1Cixoztc4NSeM5JPuOo3DwM0QX4hYmnqc",
        "Ambil Data 4/npz file/kambing 6/BED_1784435517059.npz",
    ),
    (
        "Ambil Data 4",
        "kambing 6",
        "BED_1784435638160.npz",
        "1O60r6el1CBSQC7Mut1Ru0tFWd3v3OeqC",
        "Ambil Data 4/npz file/kambing 6/BED_1784435638160.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038047851.npz",
        "1o48vcz7pKPzxKE_5gix-TaApfibQAbsv",
        "Ambil Data 5/npz file/kambing 1/BED_1785038047851.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038116931.npz",
        "1Q0mNAyl2H1wohyKOkUgv1J5pVgLxTkiB",
        "Ambil Data 5/npz file/kambing 1/BED_1785038116931.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038184017.npz",
        "1NsXjl2anj6PLKESHwl6nUKRSvVgx7Ajo",
        "Ambil Data 5/npz file/kambing 1/BED_1785038184017.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038303153.npz",
        "1RhRZGTEiIz09x6Pk43dSsMQkur_2ngx5",
        "Ambil Data 5/npz file/kambing 1/BED_1785038303153.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038395195.npz",
        "1FQ8VB7oYnVh_GVb66FLOYXcHZAhhmoXu",
        "Ambil Data 5/npz file/kambing 1/BED_1785038395195.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038521317.npz",
        "1uBq98jzx-1abzfRAXi0lkDnkWVVcfwcC",
        "Ambil Data 5/npz file/kambing 1/BED_1785038521317.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 1",
        "BED_1785038653448.npz",
        "15WMEipuypI7aaAVNcm3NZebVPxbxPuvu",
        "Ambil Data 5/npz file/kambing 1/BED_1785038653448.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785039223045.npz",
        "19p0TR_yAZGlCMTgwHxDLDIknEB_q7TYJ",
        "Ambil Data 5/npz file/kambing 2/BED_1785039223045.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785039292062.npz",
        "1V8jHyBdHH9bebm52ItUkN3_aGCmvmjwn",
        "Ambil Data 5/npz file/kambing 2/BED_1785039292062.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785039430215.npz",
        "1XY8lNgY5CWNZUJ5SF3cIBxrv-uyTaBL-",
        "Ambil Data 5/npz file/kambing 2/BED_1785039430215.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785039521330.npz",
        "1DMqjojJoB0YOZjDbO2IrXMqI0D1nSlc8",
        "Ambil Data 5/npz file/kambing 2/BED_1785039521330.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785040132895.npz",
        "1WSgmrZMGY4DtCnnu3RlyLAuWKWMGByHE",
        "Ambil Data 5/npz file/kambing 2/BED_1785040132895.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785040244019.npz",
        "1gdF9b1hz05a5Uin6E3RpPoi9NkqtbEH6",
        "Ambil Data 5/npz file/kambing 2/BED_1785040244019.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 2",
        "BED_1785040426151.npz",
        "1XeMgWfK0z_1yZpKJMIJkijB7TPYn3UNZ",
        "Ambil Data 5/npz file/kambing 2/BED_1785040426151.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785040808549.npz",
        "14A7_oCHq7qcVseJnGNrO7k-daMKExUd5",
        "Ambil Data 5/npz file/kambing 3/BED_1785040808549.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785040881568.npz",
        "1AixfxMiwwyAL3W7OQ60594qRh-vYDxVl",
        "Ambil Data 5/npz file/kambing 3/BED_1785040881568.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785040948641.npz",
        "1cCORjD-ACa4ohu7uXiRLHZAUtX04mduN",
        "Ambil Data 5/npz file/kambing 3/BED_1785040948641.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785041032711.npz",
        "1qnmlwY_AFF9PxyOl0tg5Wmw8mdyHde_C",
        "Ambil Data 5/npz file/kambing 3/BED_1785041032711.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785041137821.npz",
        "1U3JscB9BU7ufs7lt1R5K64UBqXp8TjYB",
        "Ambil Data 5/npz file/kambing 3/BED_1785041137821.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785041256002.npz",
        "1kEg9nyXeObdeHOLTOylsN7pYKWhh9lF_",
        "Ambil Data 5/npz file/kambing 3/BED_1785041256002.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 3",
        "BED_1785041377074.npz",
        "1t0LIrGooTO0AMSk5nDhlCS8UPu-o3TlS",
        "Ambil Data 5/npz file/kambing 3/BED_1785041377074.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785041757471.npz",
        "1HWbUhVG1euDiCJ1jOZn3eTzXw9B44A2P",
        "Ambil Data 5/npz file/kambing 6/BED_1785041757471.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785041836511.npz",
        "1Z6LkR7KuXAd2nQY9fTbgZMqDsjMOWNnl",
        "Ambil Data 5/npz file/kambing 6/BED_1785041836511.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785041903542.npz",
        "1V6M0rivVF9JR3Sj7OZ65OAEAGcyq_eKM",
        "Ambil Data 5/npz file/kambing 6/BED_1785041903542.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785042040676.npz",
        "1oCNXiuqXHSBTYCHYM_atcm9sJkI4J9sq",
        "Ambil Data 5/npz file/kambing 6/BED_1785042040676.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785042172821.npz",
        "1AUq88hkD-wenxbmCT8ZkIzj7kxCp-gz6",
        "Ambil Data 5/npz file/kambing 6/BED_1785042172821.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785042280911.npz",
        "1Fh6qIoRBDH8ZaGpnCRSp-EZUaX1b4wAl",
        "Ambil Data 5/npz file/kambing 6/BED_1785042280911.npz",
    ),
    (
        "Ambil Data 5",
        "kambing 6",
        "BED_1785042399023.npz",
        "1RdGNjHfHyUQBvLFEyER5ySUpPZusbqGE",
        "Ambil Data 5/npz file/kambing 6/BED_1785042399023.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643209393.npz",
        "14k8sh5-cB9HyxqQuqSrUtLvZjAsyj03v",
        "Ambil Data 6/npz file/kambing 1/BED_1785643209393.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643275409.npz",
        "1nmpLxnU_DGLpq0dtZ-23Q_hEqxYyD52n",
        "Ambil Data 6/npz file/kambing 1/BED_1785643275409.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643343500.npz",
        "1JJp7FQZeldB0PLwNfQ_sIsS0Vz6n-WyV",
        "Ambil Data 6/npz file/kambing 1/BED_1785643343500.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643510664.npz",
        "1t0uaEaTRFZhHbYr89OJomPRQjybCPWco",
        "Ambil Data 6/npz file/kambing 1/BED_1785643510664.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643673811.npz",
        "1yHjF10remM39y3-IVrAE8dd3_87dga9W",
        "Ambil Data 6/npz file/kambing 1/BED_1785643673811.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643826971.npz",
        "11MNStik-saEkjZMoKUEBG5CvzgVGVYyv",
        "Ambil Data 6/npz file/kambing 1/BED_1785643826971.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 1",
        "BED_1785643952057.npz",
        "1MokL2YrrI7b9RK9ysiJzgD0QXlC613MZ",
        "Ambil Data 6/npz file/kambing 1/BED_1785643952057.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644351492.npz",
        "14evbV8RJa_0zWf1SPWU5KFKktMTTnlqq",
        "Ambil Data 6/npz file/kambing 2/BED_1785644351492.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644418529.npz",
        "1WnZf5awGweJ_alZDWqsq1NnlPwzltYnf",
        "Ambil Data 6/npz file/kambing 2/BED_1785644418529.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644492589.npz",
        "1zAmsuTrb_Xk9MzCB8Hw7rTmWjAuR8p1R",
        "Ambil Data 6/npz file/kambing 2/BED_1785644492589.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644586668.npz",
        "1nJVylbqpGQEDm5pMfKiKd-IfmSaDIhrZ",
        "Ambil Data 6/npz file/kambing 2/BED_1785644586668.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644697794.npz",
        "1c7x3G0saW93xZrRqiBaS07ZD9LBfTQVN",
        "Ambil Data 6/npz file/kambing 2/BED_1785644697794.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644809916.npz",
        "15w-RBX19tJRy0xpwmTrpzyir8Q54v1pR",
        "Ambil Data 6/npz file/kambing 2/BED_1785644809916.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 2",
        "BED_1785644938021.npz",
        "1l3DWc_7LrbXBYN2Gb9tg3PxqEXAvnnZl",
        "Ambil Data 6/npz file/kambing 2/BED_1785644938021.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645350442.npz",
        "1YMzde_iiUhex_1l23JQ1fY0-t3znPDqe",
        "Ambil Data 6/npz file/kambing 3/BED_1785645350442.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645426472.npz",
        "1Z75KDZ-nNy3ILZ5JWZywZvQCDPOLiDYD",
        "Ambil Data 6/npz file/kambing 3/BED_1785645426472.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645499572.npz",
        "1fKBxvG5z36qqBfORkXUefgaPtrUQpXZ3",
        "Ambil Data 6/npz file/kambing 3/BED_1785645499572.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645594653.npz",
        "1bApRFkNN2eLcAo3VjHGs8KRlJS9lrMLd",
        "Ambil Data 6/npz file/kambing 3/BED_1785645594653.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645672715.npz",
        "1jIxVv-LOwvtnH9FRqyUSUgvOeV9pk5x4",
        "Ambil Data 6/npz file/kambing 3/BED_1785645672715.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645829932.npz",
        "1_WBQs0VenrpNwV9FMBg2xCOTjBFuHzRR",
        "Ambil Data 6/npz file/kambing 3/BED_1785645829932.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 3",
        "BED_1785645946600.npz",
        "1t81BnD8kaOYOp0YXB7VkGYRr3t3AF40D",
        "Ambil Data 6/npz file/kambing 3/BED_1785645946600.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646321389.npz",
        "1EwG5WPLcR30vSTHaOAybTVg6S9P4GSMB",
        "Ambil Data 6/npz file/kambing 6/BED_1785646321389.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646390488.npz",
        "11Ulelfa1oul_Pne_nNCAVh-e4RzVCpBU",
        "Ambil Data 6/npz file/kambing 6/BED_1785646390488.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646456457.npz",
        "19SvMUoMbR8b4BtHcpgsiXAxKUIupjY7f",
        "Ambil Data 6/npz file/kambing 6/BED_1785646456457.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646578599.npz",
        "1EX0Ixbty4g7F8wzV_FmLQWx1pYPU2dKJ",
        "Ambil Data 6/npz file/kambing 6/BED_1785646578599.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646656995.npz",
        "1C2Z92tNsP4XoPXHNsx1dc__pqK9ZdhrP",
        "Ambil Data 6/npz file/kambing 6/BED_1785646656995.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646760788.npz",
        "1aOKc3vFxR5rOb6VjUxRexgHwSCNdjwcB",
        "Ambil Data 6/npz file/kambing 6/BED_1785646760788.npz",
    ),
    (
        "Ambil Data 6",
        "kambing 6",
        "BED_1785646873895.npz",
        "1p-cYPQJuA4sAe-TTnxVHxgAizvlbOn4-",
        "Ambil Data 6/npz file/kambing 6/BED_1785646873895.npz",
    ),
]


def _drive_download_url(file_id: str) -> str:
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"  # noqa: E501


def _stats(image: np.ndarray) -> dict[str, Any]:
    values = np.asarray(image)
    return {
        "shape": list(values.shape),
        "dtype": str(values.dtype),
        "sha256": hashlib.sha256(values.tobytes()).hexdigest(),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p01": float(np.percentile(values, 1)),
        "p50": float(np.percentile(values, 50)),
        "p99": float(np.percentile(values, 99)),
        "dynamic_range_span": float(values.max() - values.min()),
        "nonzero_count": int(np.count_nonzero(values)),
        "zero_fraction": float(np.mean(values == 0)),
        "uint16_saturation_fraction": float(np.mean(values == 65535)),
        "finite": bool(np.all(np.isfinite(values))),
    }


class _ObservedPipeline(RadiographyPipeline):
    def __init__(self, config: ImagerPipelineConfig) -> None:
        super().__init__(config)
        self.pre_threshold: np.ndarray | None = None

    def _normalize_to_max_value(self, image: np.ndarray) -> np.ndarray:
        result = super()._normalize_to_max_value(image)
        self.pre_threshold = result.copy()
        return result

    def _crop_and_rotate(self, image: np.ndarray, detector_mode: str) -> np.ndarray:
        result = super()._crop_and_rotate(image, detector_mode)
        if not self.config.use_normalize:
            self.pre_threshold = result.copy()
        return result


def _run_state(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    method: str,
    reference: np.ndarray | None = None,
) -> dict[str, Any]:
    observed = _ObservedPipeline(
        ImagerPipelineConfig(use_threshold=True, threshold_method=method)
    )
    detected: list[float] = []
    threshold_stage: list[np.ndarray] = []
    threshold_masks: list[np.ndarray] = []
    original_detect = radiography_module.detect_threshold
    original_apply = radiography_module.apply_threshold_separation

    def detect(*args: Any, **kwargs: Any) -> float:
        observed.pre_threshold = np.asarray(args[0]).copy()
        value = float(original_detect(*args, **kwargs))
        detected.append(value)
        return value

    def apply(image: np.ndarray, threshold: float) -> np.ndarray:
        threshold_masks.append(np.asarray(image <= threshold, dtype=np.uint8))
        result = original_apply(image, threshold)
        threshold_stage.append(result.copy())
        return result

    radiography_module.detect_threshold = detect
    radiography_module.apply_threshold_separation = apply
    try:
        final = observed.process(raw, dark, flat, "BED")
    finally:
        radiography_module.detect_threshold = original_detect
        radiography_module.apply_threshold_separation = original_apply
    if observed.pre_threshold is None:
        raise RuntimeError("Canonical pipeline did not expose PRE_THRESHOLD")
    stage = threshold_stage[0] if threshold_stage else observed.pre_threshold
    threshold_mask = threshold_masks[0] if threshold_masks else None
    return {
        "requested_threshold_method": method,
        "threshold_separation_disabled": method == "none",
        "numeric_threshold": (
            None if method == "none" else (detected[0] if detected else None)
        ),
        "effective_threshold_branch": (
            "bypass" if method == "none" else "canonical_auto"
        ),
        "fallback_semantics": None,
        "pre_threshold": observed.pre_threshold,
        "threshold_stage": stage,
        "threshold_mask": threshold_mask,
        "foreground_fraction": (
            None if threshold_mask is None else float(np.mean(threshold_mask))
        ),
        "final": final,
    }


def _select_candidates() -> list[tuple[str, str, str, str, str]]:
    groups: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = defaultdict(
        list
    )
    for candidate in CANDIDATES:
        groups[(candidate[0], candidate[1])].append(candidate)
    ordered_groups = sorted(groups)
    for group in ordered_groups:
        groups[group].sort(
            key=lambda item: (int(re.search(r"(\d+)\.npz$", item[2]).group(1)), item[2])
        )
    sessions = sorted({session for session, _ in ordered_groups})
    selected: list[tuple[str, str, str, str, str]] = []
    for position in range(2):
        for session in sessions:
            session_groups = [group for group in ordered_groups if group[0] == session]
            for group in session_groups[: max(1, COHORT_CAP // len(sessions))]:
                values = groups[group]
                selected.append(values[0] if position == 0 else values[-1])
                if len(selected) == COHORT_CAP:
                    return selected
    return selected


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _npz_metadata(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        return {
            "xrayparams": _jsonable(data["xrayparams"].item()),
            "cameraparams": _jsonable(data["cameraparams"].item()),
        }


def _stats_projection(record: dict[str, Any]) -> dict[str, Any]:
    auto_iqa = record["structural_preservation"]["BED_AUTO"]
    none_iqa = record["structural_preservation"]["BED_NONE"]
    return {
        "case": record["case"],
        "session": record["session"],
        "subject": record["subject"],
        "id": record["id"],
        "gain_id": record["gain_id"],
        "source_sha256": record["source_sha256"],
        "auto_final_sha256": record["auto_final"]["sha256"],
        "none_final_sha256": record["none_final"]["sha256"],
        "auto_edge_recall": auto_iqa["edge_recall"],
        "none_edge_recall": none_iqa["edge_recall"],
        "auto_lost_informative_tile_fraction": auto_iqa[
            "lost_informative_tile_fraction"
        ],
        "none_lost_informative_tile_fraction": none_iqa[
            "lost_informative_tile_fraction"
        ],
    }


def _markdown_case_row(record: dict[str, Any]) -> str:
    auto_iqa = record["structural_preservation"]["BED_AUTO"]
    none_iqa = record["structural_preservation"]["BED_NONE"]
    return (
        f"| {record['case']} | {record['session']} / {record['subject']} | "
        f"{record['auto']['numeric_threshold']:.6f} | "
        f"{auto_iqa['edge_recall']:.4f} | {none_iqa['edge_recall']:.4f} | "
        f"{auto_iqa['lost_informative_tile_fraction']:.4f} | "
        f"{none_iqa['lost_informative_tile_fraction']:.4f} | "
        f"{record['auto_final']['mean']:.2f} | {record['none_final']['mean']:.2f} |"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/real-data-regression")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected = _select_candidates()
    records: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="mpips-bed-phase5-") as temp:
        temp_path = Path(temp)
        gain_paths: dict[str, Path] = {}
        for session, url in GAIN_URLS.items():
            target = temp_path / f"{session.replace(' ', '_')}_gain.npz"
            urllib.request.urlretrieve(
                _drive_download_url(url.rsplit("/d/", 1)[1].split("/", 1)[0]), target
            )
            gain_paths[session] = target
        gains = load_gain_catalog(gain_paths.values())
        for index, (session, subject, title, file_id, source_path) in enumerate(
            selected, 1
        ):
            source = temp_path / f"case-{index:02d}.npz"
            try:
                urllib.request.urlretrieve(_drive_download_url(file_id), source)
                radiograph = load_radiograph(source)
                if radiograph["detector_mode"] != "BED":
                    raise NPZValidationError("detector mode is not BED")
                gain = gains.require(radiograph["gain_id"])
                raw = to_uint16(radiograph["raw"], "radiograph raw")
                dark = to_uint16(gain.dark, "gain dark")
                flat = to_uint16(gain.flat, "gain flat")
                if raw.shape != dark.shape or raw.shape != flat.shape:
                    raise NPZValidationError("radiograph/gain shapes differ")
                auto = _run_state(raw, dark, flat, "auto")
                none = _run_state(raw, dark, flat, "none")
                pre_equal = np.array_equal(auto["pre_threshold"], none["pre_threshold"])
                if not pre_equal:
                    raise NPZValidationError("AUTO/NONE pre-threshold arrays differ")
                stage_metrics = {
                    "BED_AUTO": analyze_structural_preservation(
                        auto["pre_threshold"], auto["threshold_stage"]
                    ).__dict__,
                    "BED_NONE": analyze_structural_preservation(
                        none["pre_threshold"], none["threshold_stage"]
                    ).__dict__,
                }
                gain_meta = _npz_metadata(gain_paths[session])
                source_meta = _npz_metadata(source)
                gain_source_id = GAIN_URLS[session].split("/d/")[1].split("/")[0]
                record = {
                    "case": index,
                    "session": session,
                    "subject": subject,
                    "source_title": title,
                    "source_path": source_path,
                    "drive_file_id": file_id,
                    "source_sha256": sha256_file(source),
                    "source_provenance": {
                        "drive_file_id": file_id,
                        "path": source_path,
                        "title": title,
                        "sha256": sha256_file(source),
                        "id": radiograph["id"],
                        "gain_id": radiograph["gain_id"],
                        "detector_mode": radiograph["detector_mode"],
                        "raw": _stats(raw),
                        **source_meta,
                    },
                    "gain_provenance": {
                        "drive_file_id": gain_source_id,
                        "path": f"{session}/gain NPZ/{gain_paths[session].name}",
                        "title": gain_paths[session].name,
                        "sha256": sha256_file(gain_paths[session]),
                        "id": gain.id,
                        "detector_mode": gain.detector_mode,
                        "dark": _stats(dark),
                        "flat": _stats(flat),
                        **gain_meta,
                    },
                    "id": radiograph["id"],
                    "gain_id": radiograph["gain_id"],
                    "detector_mode": radiograph["detector_mode"],
                    "raw_shape": list(raw.shape),
                    "raw_dtype": str(raw.dtype),
                    "auto": {
                        k: v
                        for k, v in auto.items()
                        if k
                        not in {
                            "pre_threshold",
                            "threshold_stage",
                            "threshold_mask",
                            "final",
                        }
                    },
                    "none": {
                        k: v
                        for k, v in none.items()
                        if k
                        not in {
                            "pre_threshold",
                            "threshold_stage",
                            "threshold_mask",
                            "final",
                        }
                    },
                    "pre_threshold": _stats(auto["pre_threshold"]),
                    "pre_threshold_sha256_equal": pre_equal,
                    "auto_threshold_stage": _stats(auto["threshold_stage"]),
                    "none_threshold_stage": _stats(none["threshold_stage"]),
                    "structural_preservation": stage_metrics,
                    "auto_final": _stats(auto["final"]),
                    "none_final": _stats(none["final"]),
                    "final_sha256_equal": _stats(auto["final"])["sha256"]
                    == _stats(none["final"])["sha256"],
                }
                records.append(record)
            except (OSError, KeyError, ValueError, NPZValidationError) as exc:
                excluded.append(
                    {
                        "session": session,
                        "subject": subject,
                        "source_title": title,
                        "drive_file_id": file_id,
                        "reason": str(exc),
                        "classification": "invalid",
                    }
                )

    selected_ids = {item[3] for item in selected}
    inventory_candidates = [
        {
            "session": session,
            "subject": subject,
            "title": title,
            "drive_file_id": file_id,
            "source_path": source_path,
            "classification": (
                "eligible" if file_id in selected_ids else "valid but unselected"
            ),
        }
        for session, subject, title, file_id, source_path in CANDIDATES
    ]
    classification = "BED THRESHOLD POLICY UNRESOLVED"
    decision = {
        "reference_comparability": "NON-COMPARABLE",
        "classification_basis": (
            "NONE is an identity/bypass control and pre-threshold equality is "
            "asserted, but no trustworthy exact same-acquisition processed/reference "
            "ground truth was established; AUTO changes alone cannot support bypass."
        ),
    }
    payload = {
        "phase": "PHASE 5 — BED THRESHOLD POLICY EVIDENCE CHARACTERIZATION",
        "governing_task_revision": "e230ffc6d1ae86e09cba706c46f4632979d547b1",
        "source_folder": SOURCE_FOLDER,
        "source_access": "read-only",
        "inventory": {
            "acquisition_candidates": 196,
            "gain_npz": 6,
            "calibration_or_processed_npz": 4,
            "folders_visited": 96,
            "candidate_classification_counts": {
                "eligible": len(records),
                "valid but unselected": len(CANDIDATES) - len(selected),
                "invalid": len(excluded),
                "non-BED": 0,
                "duplicate": 0,
                "gain-unresolved": 0,
                "calibration-unresolved": 0,
            },
            "candidates": inventory_candidates,
        },
        "selection_rule": (  # noqa: E501
            "Lexicographic session/subject groups; stable numeric acquisition "
            f"ordering; first/last per group; round-robin; cap {COHORT_CAP}; frozen "
            "before processing."
        ),
        "selected_candidates": [
            {
                "session": s,
                "subject": u,
                "title": t,
                "drive_file_id": i,
                "source_path": p,
            }
            for s, u, t, i, p in selected
        ],
        "excluded": excluded,
        "cases": records,
        "classification": classification,
        "decision": decision,
        "limitations": [
            "Processed/reference and calibration trees were inventoried but not "
            "treated as ground truth.",
            "No calibration was substituted or generated; paired runs used the "
            "canonical no-remap array path.",
            "IQA is stage-local and not a clinical or diagnostic claim.",
        ],
    }
    json_path = args.output_dir / "bed-threshold-policy-characterization.json"
    csv_path = args.output_dir / "bed-threshold-policy-characterization.csv"
    md_path = args.output_dir / "bed-threshold-policy-characterization.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    fields = [
        "case",
        "session",
        "subject",
        "id",
        "gain_id",
        "source_sha256",
        "auto_final_sha256",
        "none_final_sha256",
        "auto_edge_recall",
        "none_edge_recall",
        "auto_lost_informative_tile_fraction",
        "none_lost_informative_tile_fraction",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow(_stats_projection(record))
    deltas = [r["auto_final"]["mean"] - r["none_final"]["mean"] for r in records]
    md_path.write_text(
        "\n".join(
            [
                "# BED Threshold Policy Characterization",
                "",
                f"Classification: **{classification}**",
                "",
                f"Source: `{SOURCE_FOLDER}` (read-only). Inventory: 196 "
                "acquisition NPZ candidates, 6 gain NPZ files, 4 calibration or "
                "processed NPZ files, 96 folders visited.",
                "",
                "Selection was frozen before processing: lexicographic "
                "session/subject groups, stable acquisition ordering, first/last "
                f"distinct acquisitions, round-robin, maximum {COHORT_CAP}.",
                "",
                f"Selected and successfully paired cases: {len(records)}; "
                f"excluded: {len(excluded)}.",
                "",
                f"Final AUTO-minus-NONE mean-intensity delta median: "
                f"{median(deltas) if deltas else 'NON-COMPARABLE'}.",
                "",
                "Reference comparability: **NON-COMPARABLE**. NONE is an identity "
                "control, not a ground-truth reference; classification therefore "
                "remains unresolved.",
                "",
                "## Case-level evidence",
                "",
                "| Case | Session / subject | AUTO threshold | AUTO edge recall | "
                "NONE edge recall | AUTO lost informative tiles | "
                "NONE lost informative tiles | AUTO final mean | NONE final mean |",
                "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
                *[_markdown_case_row(record) for record in records],
                "",
                "## Grouping and conflicts",
                "",
                "The complete inventory and selection manifest are in the JSON "
                "artifact. Selected cases are distributed across all six sessions "
                "and the selection was frozen before either result was inspected. "
                "Case-level direction and outliers must be interpreted with the "
                "NON-COMPARABLE reference limitation above.",
                "",
                "IQA compares each threshold-stage output with the same-geometry "
                "normalized pre-threshold image using "
                "`mpips.iqa.analyze_structural_preservation`. No clinical or "
                "diagnostic conclusion is made.",
                "",
                "The classification is decision support only and does not change "
                "BED runtime policy.",
                "",
            ]
        )
    )
    print(
        json.dumps(
            {
                "classification": classification,
                "cases": len(records),
                "excluded": len(excluded),
                "output": str(args.output_dir),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
