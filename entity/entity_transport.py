# -*- coding:utf-8 -*-

import logging
import numpy as np
import pandas as pd
import collections
import os
import urllib.request  #import urllib
from pathlib import Path



def downloader_stop_name(overwrite_file=False):
    stop_name_path = 'stop_name_df.csv'

    if not Path(stop_name_path).exists() or overwrite_file:
        STOP_NAME_URL = "https://drive.google.com/uc?id=1hmGT053H-pLjlIlv0AukFVYNHQW69DV4"
        urllib.request.urlretrieve(STOP_NAME_URL, stop_name_path)

    stop_name_df = pd.read_csv(stop_name_path)
    return stop_name_df



def do_predict(string):
    
    stop_name_df = downloader_stop_name()
    


do_predict("서울역")