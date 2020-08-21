# -*- coding:utf-8 -*-
import folium
import json
import requests
import xmltodict

import numpy as np

#
service_key = ''
service_url = 'http://ws.bus.go.kr/api/rest/pathinfo'


def get_location_info(desc_location):
    param = {'stSrch': desc_location}
    url = '%s/getLocationInfo?ServiceKey=%s' % (service_url, service_key)
    res = requests.get(url, params=param)

    return res


def get_path_info_by_bus_n_subway(start_loc, end_loc):
    param = {'startX': start_loc['gpsX'], 'startY': start_loc['gpsY'], 
             'endX': end_loc['gpsX'], 'endY': end_loc['gpsY']}
    url = '%s/getPathInfoByBusNSub?ServiceKey=%s' % (service_url, service_key)
    res = requests.get(url, params=param)

    return res


def response_to_dict(res):
    return json.loads(json.dumps(xmltodict.parse(res.text)))


def visualization_in_map(item_list):
    Xs, Ys = zip(*[(float(item['gpsX']), float(item['gpsY'])) for item in item_list])
    
    mean_loc = (np.mean(Ys), np.mean(Xs))
    
    map_osm = folium.Map(location=mean_loc, zoom_start=17)
    
    for i, item in enumerate(item_list):
        marker = folium.Marker((item['gpsY'], item['gpsX']),
                              popup='%d. %s' % (i+1, item['poiNm']),
                              icon=folium.Icon(color='red'))

        marker.add_to(map_osm)
        
    return map_osm


def print_routes(item_list):
    output_list = []
    for i, item in enumerate(item_list):
        output_text = ""
        distance = item['distance']
        time = item['time']
        path_list = item['pathList']
        
        output_text += f'{i+1}. 거리({int(distance)}), 시간({ int(time)})'
        print(output_list)
        # for path in path_list:
        #     if 'railLinkList' not in path: # bus
        #         output_list.append(' (%s 버스) %s -> %s' % (path['routeNm'], path['fname'], path['tname']))
        #     else: # subway
        #         output_list.append(' (지하철) %s -> 환승 %d번 -> %s(%s)' % (path['fname'], len(path['railLinkList'])-2, path['tname'], path['routeNm']))
        
        output_list.append(output_text)
    return output_list

def printer(output_list):
    output_text=""
    for text in output_list:
        output_text += f'</br>{text}' 
    return output_text  





def process_input(recv_value): #entity
    # recv_value["input"]

    # 질의어에서 location 추출해내기
    loc_from = "강남역"
    loc_to = "서울역"


    res = get_location_info(loc_from)
    start_dict = response_to_dict(res)

    res = get_location_info(loc_to)
    end_dict = response_to_dict(res)


    # 목록 출력
    res = get_path_info_by_bus_n_subway(start_dict['ServiceResult']['msgBody']['itemList'][0],
                                    end_dict['ServiceResult']['msgBody']['itemList'][0])
    
    route_dict = response_to_dict(res)
    output = printer(print_routes(route_dict['ServiceResult']['msgBody']['itemList']))
    

    return output 

# print(process_input())
