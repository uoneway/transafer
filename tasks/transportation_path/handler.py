# -*- coding:utf-8 -*-
import datetime
import folium
import itertools
import json
import pickle
import requests
import time
import warnings
import xmltodict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from folium.features import DivIcon

# local modules
from .config import odsay_api_key, seoul_api_key


seoul_api_url = 'http://ws.bus.go.kr/api/rest/pathinfo'
odsay_api_url = 'https://api.odsay.com/v1/api/'

BUS_SPEED_MEAN = 18.7 * 1000  # 미터 https://www.index.go.kr/potal/stts/idxMain/selectPoSttsIdxSearch.do?idx_cd=4081&stts_cd=408102

getout_bus_prob_m_df = None
subway_congestion_dict = None
subway_risk_dict = None
bus_risk_dict = None


def init_handler(data_dir='tasks/transportation_path/dataset/'):
    global getout_bus_prob_m_df, subway_congestion_dict, subway_risk_dict, bus_risk_dict

    if not getout_bus_prob_m_df:
        # 버스 노선/정류소별 일별/시간대별 데이터 가져오기
        getout_bus_prep_file = data_dir + "getout_bus_prep_m_df(202005)_min.csv"
        getout_bus_prep_m_df = pd.read_csv(getout_bus_prep_file)
        getout_bus_prep_m_df = getout_bus_prep_m_df.astype({'TIME': 'int',
                                                            'BUS_ROUTE_NO': 'str'})

    if not subway_congestion_dict:
        with open(data_dir + 'station_congestion_2015.pkl', 'rb') as file:
            subway_congestion_df = pickle.load(file)

        subway_congestion_dict = subway_congestion_df.set_index(
            ['사용일', '역번', '구분']).to_dict('index')

        with open(data_dir + 'station_congestion_2015_est_5_8.pkl', 'rb') as file:
            subway_congestion_58_df = pickle.load(file)

        subway_congestion_dict.update(subway_congestion_58_df.set_index(
            ['사용일', '역번', '구분']).to_dict('index'))

        df = pd.read_csv(data_dir + '서울특별시 노선별 지하철역 정보(신규)_fix.csv')
        subway_code = {}

        for i, row in df.iterrows():
            subway_code[row['전철역코드']] = row['외부코드']

        subway_congestion_dict = {
            (key[0], subway_code.get(str(key[1]), str(key[1])), key[2]):value
            for key, value in subway_congestion_dict.items()
        }

    if not subway_risk_dict:
        with open(data_dir + 'subway_risk_dict.pkl', 'rb') as file:
            subway_risk_dict = pickle.load(file)

        subway_risk_dict = {key: value/key
                            for key, value in subway_risk_dict.items()}

    if not bus_risk_dict:
        with open(data_dir + 'bus_risk_dict.pkl', 'rb') as file:
            bus_risk_dict = pickle.load(file)

        bus_risk_dict = {key: value/key for key, value in bus_risk_dict.items()}

    return None


def get_location_info(desc_location):
    param = {'stSrch': desc_location}
    url = '%s/getLocationInfo?ServiceKey=%s' % (seoul_api_url, seoul_api_key)
    res = requests.get(url, params=param)

    return res


def response_to_dict(res, type='xml'):
    if type == 'xml':
        return json.loads(json.dumps(xmltodict.parse(res.text)))
    elif type == 'json':
        return json.loads(res.text)


def draw_locations_on_map(item_list):
    Xs, Ys = zip(*[(float(item['gpsX']), float(item['gpsY'])) for item in item_list])
    mean_loc = (Ys[0], Xs[0])
    map_osm = folium.Map(location=mean_loc, zoom_start=16)

    for i, item in enumerate(item_list):
        loc = (item['gpsY'], item['gpsX'])

        marker = folium.Marker(loc,
                               popup='%d. %s' % (i+1, item['poiNm']),
                               icon=DivIcon(
                                   icon_size=(50,36),
                                   icon_anchor=(25,18),
                                   html='<div style="font-size: 18pt; color: white; text-align: center;">%d</div>' % (i+1)))
                              #icon=folium.Icon(color='red'))

        marker.add_to(map_osm)
        map_osm.add_child(folium.CircleMarker(loc, fill=True, radius=15, color='crimson', fill_opacity=0.5))

    return map_osm


def ask_origin(output):
    res = get_location_info(output)
    res_dict = response_to_dict(res)

    if res_dict['ServiceResult']['msgHeader']['headerCd'] == '4': # 결과 없음
        return None, 0

    item_list = res_dict['ServiceResult']['msgBody']['itemList']

    if not isinstance(item_list, list):
        item_list = [item_list]

    map_osm = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map_osm.save(html_path)

    return html_path, [(item['poiNm'], item['gpsX'], item['gpsY']) for item in item_list]


def ask_destination(output):
    res = get_location_info(output)
    res_dict = response_to_dict(res)

    if res_dict['ServiceResult']['msgHeader']['headerCd'] == '4': # 결과 없음
        return None, 0

    item_list = res_dict['ServiceResult']['msgBody']['itemList']

    if not isinstance(item_list, list):
        item_list = [item_list]

    map_osm = draw_locations_on_map(item_list)

    html_path = 'static/maps/map_%s.html' % (repr(time.time()))
    map_osm.save(html_path)

    return html_path, [(item['poiNm'], item['gpsX'], item['gpsY']) for item in item_list]


def get_path_info(start_loc, end_loc):
    print(start_loc, end_loc)

    param = {
        'apiKey': odsay_api_key,
        'SX': start_loc[1],
        'SY': start_loc[2],
        'EX': end_loc[1],
        'EY': end_loc[2]
    }
    res = requests.get(odsay_api_url + 'searchPubTransPathR', params=param)

    return res


def search_routes(start_loc, end_loc):
    res = get_path_info(start_loc, end_loc)
    res_dict = json.loads(res.text)
    route_list = res_dict['result']['path']

    return route_list


def draw_routes(route_list):
    pass
