import geopandas as gpd
import osmnx as ox
import momepy
from collections import Counter
import pandas as pd
import json
import requests
import shapely.geometry
from shapely.geometry import Polygon
from shapely.geometry import LineString
from shapely.prepared import prep
from datetime import datetime, timedelta

import random

from shapely.geometry import Polygon
from shapely.geometry import Point as pit

import numpy as np

import rhino3dm as rg
import math
import copy
import math
import time

import wlftwo_utils_cero as wlf2cero


#@title Play function
#@markdown Function for HOPS
# populationThreshold = pt
#     junctionType = jt
#     branchingSteps = bs
#     growthAngle = ga
#     StreetBlockSize=sbs

def getEdges(poly, iter, pt, jt, bs, ga, sbs):

    class configuration:
        def __init__(self, segmentLength = None, growthAngle = None, angleResolution = None, waterAngleShift = None, branchingSteps = None, junctionType = None, populationThreshold = None, initialDirection = None, heatmap = [], population = [], boundingBox = None):
                            
            if segmentLength == None:
                self.SEGMENT_LENGTH = 33.0
            else:
                self.SEGMENT_LENGTH = segmentLength
                                
            if growthAngle == None:
                self.BRANCH_ANGLE = 5.0
            else:
                self.BRANCH_ANGLE = growthAngle
                                
            if angleResolution == None:
                self.BRANCH_ANGLE_STEPS = 7
            else:
                self.BRANCH_ANGLE_STEPS = angleResolution
                                
            if waterAngleShift == None:
                self.WATER_ANGLE_SHIFT = 0.0
            else:
                self.WATER_ANGLE_SHIFT = waterAngleShift
                            
            if branchingSteps == None:
                self.BRANCH_STEP = 2
            else:
                self.BRANCH_STEP = branchingSteps
                            
            if junctionType != 0 and junctionType != 1 and junctionType != 2:
                junctionType = 0
            if junctionType == 0: # crossing
                self.BRANCH_STEP_LEFT = 0 #branching to left every x branches
                self.BRANCH_STEP_RIGHT = 0 #branching to right every x branches
            elif junctionType == 1: # t-junction start left
                self.BRANCH_STEP_LEFT = 0 
                self.BRANCH_STEP_RIGHT = math.ceil(float(self.BRANCH_STEP) / 2.0) 
            elif junctionType == 2: # t-junction start right
                self.BRANCH_STEP_LEFT = math.ceil(float(self.BRANCH_STEP) / 2.0)
                self.BRANCH_STEP_RIGHT = 0 
                    
            if populationThreshold == None:
                self.POPULATION_THRESHOLD = 0.85
            elif populationThreshold < 0.0:
                self.POPULATION_THRESHOLD = 0.0
            elif populationThreshold > 1.0:
                self.POPULATION_THRESHOLD = 1.0
            else:
                self.POPULATION_THRESHOLD = populationThreshold
            
            if initialDirection != 0 and initialDirection != 1 and initialDirection != 2:
                initialDirection = 0
            self.INITIAL_DIRECTION = initialDirection
            # ignore intersections with less than this degrees angle
            self.MINIMUM_INTERSECTION_DEVIATION = 10.0
            # maximum distance to connect roads
            self.ROAD_SNAP_DISTANCE_FACTOR = 0.9
            self.ROAD_SNAP_DISTANCE = self.SEGMENT_LENGTH * self.ROAD_SNAP_DISTANCE_FACTOR
            # close road with already similar direction..
            self.ROAD_SIMILARITY_DISTANCE_FACTOR = 0.66
            self.ROAD_SIMILARITY_DISTANCE = self.SEGMENT_LENGTH * self.BRANCH_STEP * self.ROAD_SIMILARITY_DISTANCE_FACTOR
            self.ROAD_SIMILARITY_MINIMUM_DEVIATION_ANGLE = 30.0
            self.HEATMAP = heatmap
            self.POPULATION = population
            self.BOUNDS = boundingBox
            # grow to the right and left initially
    
    #GRAPH
    # G = ox.graph_from_place(place_name, network_type='walk', simplify=True) #other network types: drive, bike, drive_service, all, all_private
    # poly= '[2.168512,41.406815],[2.186193,41.393101],[2.205334,41.406686],[2.186537,41.420268],[2.168512,41.406815]@[2.17555,41.406943],[2.187395,41.397286],[2.19924,41.406879],[2.186279,41.416599],[2.17555,41.406943]@'
    final_b = poly.rstrip(poly[-1])
    final_b = final_b.replace("[", "")
    final_b = final_b.replace("]", "")
    final_b = final_b.split('@')
    list_pois = []
    for i in range(len(final_b)):
        ya = [j.split() for j in final_b[i].split(',') if j!='']
        ya = [item for sublist in ya for item in sublist]
        ya = [float(i) for i in ya]
        lat_point_list = ya[0::2]
        lon_point_list = ya[1::2]

        x = lon_point_list
        y = lat_point_list
        point_central = lat1,lng1 =sum(x)/len(x), sum(y)/len(y) 

        a = zip(lat_point_list, lon_point_list)
        polygon_geom = Polygon(a)
        crs = 'epsg:3857'
        polygon = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[polygon_geom])
        polygon= polygon.iloc[0]['geometry'] 
        list_pois.append(polygon)

    polygon = list_pois[0]
    G = ox.graph_from_polygon(polygon, network_type = 'drive',simplify=False)
    gdf_proj_streets_good = ox.graph_to_gdfs(G, nodes=False)

    # G = ox.graph_from_bbox(north, south, east, west, network_type='drive',simplify=True)
    G_projected = ox.projection.project_graph(G)

    hwy_speeds = {"residential": 35, "secondary": 50, "tertiary": 60}
    G_projected = ox.add_edge_speeds(G_projected, hwy_speeds)

    # calculate travel time (seconds) for all edges
    G_projected = ox.add_edge_travel_times(G_projected)

    # see mean speed/time values by road type
    gdf_proj_streets = ox.graph_to_gdfs(G_projected, nodes=False)
    #cull
    gdf_proj_streets["highway"] = gdf_proj_streets["highway"].astype(str)
    gdf_proj_streets.groupby("highway")[["length", "speed_kph", "travel_time"]].mean().round(1)

    crs = 3857

    #BUILDINGS
    tag_building = {"building": True}
    gdf_building = ox.geometries.geometries_from_polygon(polygon, tag_building)
    buildings_gdf = ox.projection.project_gdf(gdf_building)
    buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    buildings_gdf = buildings_gdf.explode(index_parts=True)
    buildings_gdf.reset_index(inplace=True, drop=True)

    #MOMEPY
    street_prof = momepy.StreetProfile(gdf_proj_streets, buildings_gdf)
    ## WIDTHs
    gdf_proj_streets['widths'] = street_prof.w
    # array_width = gdf_proj_streets.widths.values
    # widths = array_width.tolist()

    ## WIDTH_deviations
    gdf_proj_streets['width_deviations'] = street_prof.wd
    # array_width_deviations = gdf_proj_streets.width_deviations.values
    # width_deviations = array_width_deviations.tolist()

    ## OPENNESS
    gdf_proj_streets['openness'] = street_prof.o
    # array_openness= gdf_proj_streets.openness.values
    # openness = array_openness.tolist()

    primal = momepy.gdf_to_nx(gdf_proj_streets, approach='primal')

    #Closeness centrality could be simplified as average distance to every other node from each node
    #Local closeness
    # #To measure local closeness_centrality we need to specify radius (how far we should go from each node). We
    # can use topological distance (e.g. 5 steps, then radius=5) or metric distance (e.g. 400 metres) - then radius=400 and
    # distance= lenght of each segment saved as a parameter of each edge. By default, momepy saves length as mm_len.
    # Weight parameter is used for centrality calculation. Again, we can use metric weight (using the same attribute as
    # above) or no weight (weight=None) at all. Or any other attribute we wish.
    primal = momepy.closeness_centrality(primal, radius=40, name='closeness400',distance='mm_len', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness400')

    # Global closeness
    # Global closeness centrality is a bit simpler as we do not have to specify radius and distance, the rest remains the same.
    primal = momepy.closeness_centrality(primal, name='closeness_global', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness_global')

    # Betweenness
    # Betweenness centrality measures the importance of each node or edge for the travelling along the network. It measures
    # how many times is each node/edge used if we walk using the shortest paths from each node to every other.
    # We have two options how to measure betweenness on primal graph - on nodes or on edges.

    # Node-based
    # Node-based betweenness, as name suggests, measures betweennes of each node - how many times we would walk
    # through node.

    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_n', mode='nodes', weight='mm_len')

    momepy.mean_nodes(primal, 'betweenness_metric_n')

    # Edge-based
    # Edge-based betweenness does the same but for edges. How many times we go through each edge (street)
    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_e', mode='edges', weight='mm_len')
    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    # Straightness
    # While both closeness and betweenness are generally used in many applications of network analysis, straightness
    # centrality is specific to street networks as it requires geographical element. It is measured as a ratio between real and
    # Euclidean distance while waking from each node to every other
    primal = momepy.straightness_centrality(primal)
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'straightness')

    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    ## closeness400
    gdf_proj_streets['closeness400']=primal_gdf.closeness400.values
    # array_closeness400= primal_gdf.closeness400.values
    # closeness400 = array_closeness400.tolist()

    ## closeness_global
    gdf_proj_streets['closeness_global']=primal_gdf.closeness_global.values
    # array_closeness_global= primal_gdf.closeness_global.values
    # closeness_global = array_closeness_global.tolist()

    ## betweenness_metric_n
    gdf_proj_streets['betweenness_metric_n']=primal_gdf.betweenness_metric_n.values
    # array_betweenness_metric_n= primal_gdf.betweenness_metric_n.values
    # betweenness_metric_n = array_betweenness_metric_n.tolist()

    ## betweenness_metric_e
    gdf_proj_streets['betweenness_metric_e']=primal_gdf.betweenness_metric_e.values
    # array_betweenness_metric_e= primal_gdf.betweenness_metric_e.values
    # betweenness_metric_e = array_betweenness_metric_e.tolist()

    ## straightness
    gdf_proj_streets['straightness']=primal_gdf.straightness.values
    # array_straightness= primal_gdf.straightness.values
    # straightness = array_straightness.tolist()

    #SPEED
    # array_speed = gdf_proj_streets.speed_kph.values
    # speed = array_speed.tolist()

    #TRAVEL
    # array_travel = gdf_proj_streets.travel_time.values
    # travel = array_travel.tolist()

    # # /////////////////////////////////////////////
    # G_proj = ox.projection.project_graph(G_projected, to_crs=crs)

    G_proj = ox.projection.project_graph(G_projected, to_crs=crs)
    #FOOD
    key_food_a = "amenity" 
    value_FOOD_a = ["bar",
                "biergarten",
                "restaurant",
                "food_court",
                "ice_cream",
                "pub",
                "cafe",
                "fast_food"]
    tags_food_a = {key_food_a: value_FOOD_a}

    key_food_b = "shop" 
    value_FOOD_b = ["alcohol",
                "bakery",
                "beverages",
                "brewing_supplies",
                "butcher",
                "cheese",
                "chocolate",
                "coffee",
                "confectionery",
                "convenience",
                "deli",
                "dairy",
                "frozen_food",
                "greengrocer",
                "health_food",
                "ice_cream",
                "pasta",
                "pastry",
                "seafood",
                "spices",
                "tea",
                "wine",
                "department_store",
                "general",
                "kiosk",
                "mall",
                "supermarket",
                "wholesale"]
    tags_food_b = {key_food_b: value_FOOD_b}

    tags_food = dict(tags_food_a, **tags_food_b)

    gdf_FOOD = ox.geometries.geometries_from_polygon(polygon, tags_food)
    gdf_pts_FOOD = gdf_FOOD.loc[gdf_FOOD.geometry.geometry.type=='Point']
    if not gdf_pts_FOOD.empty:
        gdf_pts_proj_FOOD = ox.projection.project_gdf(gdf_pts_FOOD, to_crs=crs)
        # Calculate distances to
        G_dist_FOOD = ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_FOOD['geometry'].x, Y=gdf_pts_proj_FOOD['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_FOOD = Counter(G_dist_FOOD)
        # Initialize empty list for values
        food = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_FOOD = occurences_FOOD[gdf_proj_streets.loc[i].name]
            food.append(occurence_FOOD)
        gdf_proj_streets['food'] = food
    else:
        food = [0] * len(gdf_proj_streets)
        gdf_proj_streets['food'] = food
    # # /////////////////////////////////////////////

    # #education
    key_education = "amenity" 
    value_education = ["college",
                "kindergarten",
                "library",
                "university",
                "school"]

    tags_education = {key_education: value_education}
    gdf_education = ox.geometries.geometries_from_polygon(polygon, tags_education)
    gdf_pts_education = gdf_education.loc[gdf_education.geometry.geometry.type=='Point']
    if not gdf_pts_education.empty:
        gdf_pts_proj_education = ox.projection.project_gdf(gdf_pts_education, to_crs=crs)
        # Calculate distances to
        G_dist_education= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_education['geometry'].x, Y=gdf_pts_proj_education['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_education = Counter(G_dist_education)
        # Initialize empty list for values
        education = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_education = occurences_education[gdf_proj_streets.loc[i].name]
            education.append(occurence_education)
        gdf_proj_streets['education'] = education
    else:
        education = [0] * len(gdf_proj_streets)
        gdf_proj_streets['education'] = education

    # # /////////////////////////////////////////////

    # #transport
    key_transport = "amenity" 
    value_transport = ["bicycle_parking",
                "bus_station",
                "charging_station",
                "ferry_terminal",
                "fuel",
                "motorcycle_parking",
                "parking",
                "parking_entrance",
                "parking_space",
                "taxi"]                

    tags_transport = {key_transport: value_transport}
    gdf_transport = ox.geometries.geometries_from_polygon(polygon, tags_transport)
    gdf_pts_transport = gdf_transport.loc[gdf_transport.geometry.geometry.type=='Point']
    if not gdf_pts_transport.empty:
        gdf_pts_proj_transport = ox.projection.project_gdf(gdf_pts_transport, to_crs=crs)
        # Calculate distances to
        G_dist_transport= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_transport['geometry'].x, Y=gdf_pts_proj_transport['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_transport = Counter(G_dist_transport)
        # Initialize empty list for values
        transport = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_transport = occurences_transport[gdf_proj_streets.loc[i].name]
            transport.append(occurence_transport)
        gdf_proj_streets['transport'] = transport
    else:
        transport = [0] * len(gdf_proj_streets)
        gdf_proj_streets['transport'] = transport

    # #shop
    key_shop = "shop" 
    value_shop = ["baby_goods",
                "bag",
                "boutique",
                "clothes",
                "fabric",
                "fashion_accessories",
                "jewelry",
                "leather",
                "sewing",
                "shoes",
                "tailor",
                "watches",
                "wool",
                "charity",
                "second_hand",
                "variety_store",
                "beauty",
                "chemist",
                "cosmetics",
                "erotic",
                "hairdresser",
                "hairdresser_supply",
                "hearing_aids",
                "herbalist",
                "perfumery",
                "tattoo"]                

    tags_shop = {key_shop: value_shop}
    gdf_shop = ox.geometries.geometries_from_polygon(polygon, tags_shop)
    gdf_pts_shop = gdf_shop.loc[gdf_shop.geometry.geometry.type=='Point']
    if not gdf_pts_shop.empty:
        gdf_pts_proj_shop = ox.projection.project_gdf(gdf_pts_shop, to_crs=crs)
        # Calculate distances to
        G_dist_shop= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_shop['geometry'].x, Y=gdf_pts_proj_shop['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_shop = Counter(G_dist_shop)
        # Initialize empty list for values
        shop = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_shop = occurences_shop[gdf_proj_streets.loc[i].name]
            shop.append(occurence_shop)
        gdf_proj_streets['shop'] = shop
    else:
        shop = [0] * len(gdf_proj_streets)
        gdf_proj_streets['shop'] = shop
    # /////////////////////////////////////////////
    # #vegetation
    tags_vegetation = {
        'natural':True,
    }

    gdf_vegetation = ox.geometries.geometries_from_polygon(polygon, tags_vegetation)
    gdf_pts_vegetation = gdf_vegetation.loc[gdf_vegetation.geometry.geometry.type=='Point']
    if not gdf_pts_vegetation.empty:
        gdf_pts_proj_vegetation = ox.projection.project_gdf(gdf_pts_vegetation, to_crs=crs)
        # Calculate distances to
        G_dist_vegetation= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_vegetation['geometry'].x, Y=gdf_pts_proj_vegetation['geometry'].y, interpolate=None, return_dist=False)
        # Count occurences in distance df
        occurences_vegetation = Counter(G_dist_vegetation)
        # Initialize empty list for values
        vegetation = []
        # Map occurences to G_edge df
        for i in gdf_proj_streets.index:
            occurence_vegetation = occurences_vegetation[gdf_proj_streets.loc[i].name]
            vegetation.append(occurence_vegetation)
        gdf_proj_streets['vegetation'] = vegetation
    else:
        vegetation = [0] * len(gdf_proj_streets)
        gdf_proj_streets['vegetation'] = vegetation
    # /////////////////////////////////////////////
    locations = [point_central]
    dt_string = '20211231'
    dt_stringfrom = '19901231'

    parameters = 'T2M,WS2M,WD2M,QV2M,CLOUD_AMT,TS,PW,DIRECT_ILLUMINANCE,DIFFUSE_ILLUMINANCE,ALLSKY_SFC_UVA'

    url = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters="+parameters+"&community=RE&longitude={longitude}&latitude={latitude}&start="+dt_stringfrom+"&end="+dt_string+"&format=JSON"

    data = []
    base_url = url
    for latitude, longitude in locations:
        api_request_url = base_url.format(longitude=longitude, latitude=latitude)
        response = requests.get(url=api_request_url, verify=True, timeout=300.00) 
        content = json.loads(response.content.decode('utf-8'))
        dfa = pd.json_normalize(content['geometry'])
        dfb = pd.json_normalize(content['properties'])
        dfc = dfa.join(dfb)
        data.append(dfc)

    result = pd.concat(data)

    def get_climate_value(parameter_string, tag):
        """Get value of specific data"""
        new_points = pd.DataFrame()
        # new_points = address_nasa.iloc[[0]].copy()
        for i in range(2001,2022):
            a = 'df_new_year'+str(i)
        # print(a)
        b = result.copy()
        year = parameter_string + str(i)
        c = b.filter(like=year, axis=1)
        c_new = c.copy()
        anual = str(i)
        c_new[anual] = c_new.sum(axis=1)/len(c_new.columns)
        c_new = [float(u) for u in c_new[anual]]
        new_points[anual] = c_new
        new_points['tag'] = tag

        new_points_new = new_points.copy()
        new_points_new = new_points.melt(id_vars=["tag"], var_name="start_date")
        new_points_new = new_points_new[['start_date', 'tag','value']]
        new_points_new['value'] = new_points_new.rename({'value': 'value_'+tag}, axis=1, inplace=True)
        new_points_new = new_points_new[['start_date', 'tag','value_'+tag]]
        new_points_new['start_date'] = new_points_new['start_date'].astype(float)


        # Return indices and distances
        return (new_points_new)

    new_points_tm = get_climate_value('T2M.', 'temperature')
    new_points_ws = get_climate_value('WS2M.', 'windSpeed')

    new_points_wd = get_climate_value('WD2M.', 'windDirection')

    new_points_qv = get_climate_value('QV2M.', 'humidity')

    new_points_CLOUD_AMT = get_climate_value('CLOUD_AMT.', 'skyCover')

    new_points_TS = get_climate_value('TS.', 'earthTemperature')

    new_points_PW = get_climate_value('PW.', 'precipitationWater')

    new_points_DIRECT_ILLUMINANCE = get_climate_value('DIRECT_ILLUMINANCE.', 'directIlluminance')

    new_points_DIFFUSE_ILLUMINANCE = get_climate_value('DIFFUSE_ILLUMINANCE.', 'diffuseIlluminance')

    new_points_ALLSKY_SFC_UVA = get_climate_value('ALLSKY_SFC_UVA.', 'irradiation')

    def data(new_points,year):
        aaa = new_points.loc[new_points['start_date'] == year]
        value = aaa.iloc[:, 2].values[0]        
        return(value)
    year = 2021
    tempp = data(new_points_tm,year)  
    gdf_proj_streets['value_temperature'] =tempp  

    wss = data(new_points_ws,year)  
    gdf_proj_streets['value_windSpeed'] = wss

    wdd = data(new_points_wd,year)  
    gdf_proj_streets['value_windDirection'] = wdd

    qvv = data(new_points_qv,year)  
    gdf_proj_streets['value_humidity'] = qvv

    clsky = data(new_points_CLOUD_AMT,year)  
    gdf_proj_streets['value_skyCover'] = clsky

    TSs = data(new_points_TS,year)  
    gdf_proj_streets['value_earthTemperature'] = TSs

    PWw = data(new_points_PW,year)  
    gdf_proj_streets['value_precipitationWater'] = PWw

    DIRECT_ILLUMINANCEe = data(new_points_DIRECT_ILLUMINANCE,year)  
    gdf_proj_streets['value_directIlluminance'] = DIRECT_ILLUMINANCEe

    DIFFUSE_ILLUMINANCEe = data(new_points_DIFFUSE_ILLUMINANCE,year)  
    gdf_proj_streets['value_diffuseIlluminance'] = DIFFUSE_ILLUMINANCEe

    ALLSKY_SFC_UVAa = data(new_points_ALLSKY_SFC_UVA,year)  
    gdf_proj_streets['value_irradiation'] = ALLSKY_SFC_UVAa
    # gdf_proj_streets = gdf_proj_streets.to_crs(4326)

    multi_line = gdf_proj_streets_good.geometry.values
    middle_points = []
    for i in multi_line:
            x= i.centroid.x
            y= i.centroid.y
            middle_points.append(pit(x,y))

    dataframe_middle_points = pd.DataFrame()
    gdf_dataframe_middle_points = gpd.GeoDataFrame(dataframe_middle_points, geometry=middle_points)
    # gdf_dataframe_middle_points.set_crs(epsg=4326, inplace=True)

    cleaned_middle_points = gdf_dataframe_middle_points.drop_duplicates('geometry')
    cleaned_middle_points=cleaned_middle_points.reset_index(drop=True)
    index_cleaned_middle_points=cleaned_middle_points.index.tolist()

    removed_dupl_primal = primal_gdf.iloc[index_cleaned_middle_points]
    removed_dupl_lines = gdf_proj_streets.iloc[index_cleaned_middle_points]
    removed_dupl_lines_good = gdf_proj_streets_good.iloc[index_cleaned_middle_points]

    in_lst_final = []
    for i in removed_dupl_lines_good.geometry.values:
        in_lst_final.append(i.intersects(list_pois[1]))

    streets_in=[]
    streets_out=[]
    for i in range(len(in_lst_final)):

        if in_lst_final[i] == False:
            streets_out.append(removed_dupl_lines_good.geometry.values[i])

        if in_lst_final[i] == True:
            streets_in.append(removed_dupl_lines_good.geometry.values[i])
    
    dataframe_outout = pd.DataFrame()
    df_new_dataframe_outout = gpd.GeoDataFrame(dataframe_outout, geometry=streets_out)

    exploded_lines =list_pois[1].boundary

    in_lst_intersect = []
    for i in removed_dupl_lines_good.geometry.values:
        in_lst_intersect.append(i.intersects(exploded_lines))

    streets_intersect=[]
    for i in range(len(in_lst_intersect)):
        if in_lst_intersect[i] == True:
            streets_intersect.append(removed_dupl_lines_good.geometry.values[i])
    
    dataframe_intersect = pd.DataFrame()
    df_new_streets_intersect= gpd.GeoDataFrame(dataframe_intersect, geometry=streets_intersect)
    # df_new_streets_intersect.plot()

    all_points = []
    for i in streets_intersect:
        x,y = i.coords.xy
        all_points.append(pit(x[0],y[0]))
        all_points.append(pit(x[-1],y[-1]))

    points_inside=[]
    for i in all_points:
        if i.within(list_pois[1]) == True:
            points_inside.append(i)
    
    papapa_x=[]
    papapa_y=[]
    for i in points_inside:
        x,y =i.x, i.y
        papapa_x.append(x)
        papapa_y.append(y)

    palos = [(xx,yy)  for xx,yy in zip(papapa_x,papapa_y)]
    ojo_point=palos[0]
    # print(points)

    # order the points based on the known first point:
    points_new = wlf2cero.order_points(palos, 0)
    points_new.append(ojo_point)

    exploded_int_lines=[]
    for i in range(len(points_new)):
        if i < len(points_new)-1:
            exploded_int_lines.append(LineString([points_new[i], points_new[i+1]]))
        else: 
            exploded_int_lines.append(LineString([points_new[i], points_new[0]]))
    
    # min_x, min_y, max_x, max_y = world_bbox =gdf_dataframe_for_polygon_first.geometry[0].bounds
    grid_points = wlf2cero.Random_Points_in_Polygon(list_pois[0], 10000)
    dataframe_for_grid_points = pd.DataFrame()
    gdf_dataframe_for_grid_points= gpd.GeoDataFrame(dataframe_for_grid_points, geometry=grid_points)
    gdf_dataframe_for_grid_points.set_crs(4326, inplace=True)
    gdf_dataframe_for_grid_points = gdf_dataframe_for_grid_points.to_crs(3857)

    # gdf_dataframe_for_grid_points.plot()
    
    points_bbox_x = []
    points_bbox_y = []
    for a in gdf_dataframe_for_grid_points.geometry.values:
        points_bbox_x.append(a.x)
        points_bbox_y.append(a.y)

    min_x, min_y, max_x, max_y = min(points_bbox_x), min(points_bbox_y), max(points_bbox_x), max(points_bbox_y)


    array_width = removed_dupl_lines.widths.values
    widths = array_width.tolist()
    remapped_widths = wlf2cero.remap(widths)

    array_width_deviations = removed_dupl_lines.width_deviations.values
    width_deviations = array_width_deviations.tolist()
    remapped_widths_desviationss = wlf2cero.remap(width_deviations)

    array_openness= removed_dupl_lines.openness.values
    openness = array_openness.tolist()
    remapped_openness = wlf2cero.remap(openness)

    array_closeness400= removed_dupl_primal.closeness400.values
    closeness400 = array_closeness400.tolist()
    remapped_closeness400 = wlf2cero.remap(closeness400)

    array_closeness_global= removed_dupl_primal.closeness_global.values
    closeness_global = array_closeness_global.tolist()
    remapped_closeness_global = wlf2cero.remap(closeness_global)

    array_betweenness_metric_n= removed_dupl_primal.betweenness_metric_n.values
    betweenness_metric_n = array_betweenness_metric_n.tolist()
    remapped_betweenness_metric_n= wlf2cero.remap(betweenness_metric_n)

    array_betweenness_metric_e= removed_dupl_primal.betweenness_metric_e.values
    betweenness_metric_e = array_betweenness_metric_e.tolist()
    remapped_betweenness_metric_e= wlf2cero.remap(betweenness_metric_e)

    array_straightness= removed_dupl_primal.straightness.values
    straightness = array_straightness.tolist()
    remapped_straightness= wlf2cero.remap(straightness)

    array_speed = removed_dupl_lines.speed_kph.values
    speed = array_speed.tolist()
    remapped_speed= wlf2cero.remap(speed)

    array_travel = removed_dupl_lines.travel_time.values
    travel = array_travel.tolist()
    remapped_travel= wlf2cero.remap(travel)

    array_food = removed_dupl_lines.food.values
    food = array_food.tolist()
    remapped_food= wlf2cero.remap(food)

    array_education = removed_dupl_lines.education.values
    education = array_education.tolist()
    remapped_education= wlf2cero.remap(education)

    array_transport = removed_dupl_lines.transport.values
    transport = array_transport.tolist()
    remapped_transport= wlf2cero.remap(transport)

    array_shop = removed_dupl_lines.shop.values
    shop = array_shop.tolist()
    remapped_shop= wlf2cero.remap(shop)

    array_vegetation = removed_dupl_lines.vegetation.values
    vegetation = array_vegetation.tolist()
    remapped_vegetation= wlf2cero.remap(vegetation)

    array_value_temperature = removed_dupl_lines.value_temperature.values
    value_temperature = array_value_temperature.tolist()
    remapped_value_temperature= np.multiply(wlf2cero.remap(value_temperature),remapped_widths)

    array_value_windSpeed = removed_dupl_lines.value_windSpeed.values
    value_windSpeed = array_value_windSpeed.tolist()
    remapped_value_windSpeed= np.multiply(wlf2cero.remap(value_windSpeed),remapped_widths)

    array_value_windDirection = removed_dupl_lines.value_windDirection.values
    value_windDirection = array_value_windDirection.tolist()
    remapped_value_windDirection= np.multiply(wlf2cero.remap(value_windDirection),remapped_widths)

    array_value_humidity = removed_dupl_lines.value_humidity.values
    value_humidity = array_value_humidity.tolist()
    remapped_value_humidity= np.multiply(wlf2cero.remap(value_humidity),remapped_widths)

    array_value_skyCover = removed_dupl_lines.value_skyCover.values
    value_skyCover = array_value_skyCover.tolist()
    remapped_value_skyCover= np.multiply(wlf2cero.remap(value_skyCover),remapped_widths)

    array_value_earthTemperature = removed_dupl_lines.value_earthTemperature.values
    value_earthTemperature = array_value_earthTemperature.tolist()
    remapped_value_earthTemperature= np.multiply(wlf2cero.remap(value_earthTemperature),remapped_widths)

    array_value_precipitationWater = removed_dupl_lines.value_precipitationWater.values
    value_precipitationWater = array_value_precipitationWater.tolist()
    remapped_value_precipitationWater= np.multiply(wlf2cero.remap(value_precipitationWater),remapped_widths)

    array_value_directIlluminance = removed_dupl_lines.value_directIlluminance.values
    value_directIlluminance = array_value_directIlluminance.tolist()
    remapped_value_directIlluminance= np.multiply(wlf2cero.remap(value_directIlluminance),remapped_widths)

    array_value_diffuseIlluminance = removed_dupl_lines.value_diffuseIlluminance.values
    value_diffuseIlluminance = array_value_diffuseIlluminance.tolist()
    remapped_value_diffuseIlluminance= np.multiply(wlf2cero.remap(value_diffuseIlluminance),remapped_widths)

    array_value_irradiation = removed_dupl_lines.value_irradiation.values
    value_irradiation = array_value_irradiation.tolist()
    remapped_value_irradiation= np.multiply(wlf2cero.remap(value_irradiation),remapped_widths)

    array_length = removed_dupl_lines.length.values
    length = array_length.tolist()
    remapped_traffic= np.multiply(wlf2cero.remap(length),remapped_widths)
    remapped_traffic= np.multiply(remapped_traffic,remapped_speed)

    remapped_noise= np.multiply(wlf2cero.remap(length),remapped_widths)
    remapped_noise= np.multiply(remapped_noise,remapped_speed)
    remapped_noise= np.multiply(remapped_noise,remapped_shop)

    dataframe_lslssls = pd.DataFrame()
    lslssls= gpd.GeoDataFrame(dataframe_lslssls, geometry=removed_dupl_lines.centroid)
    lslssls['width'] = remapped_widths
    lslssls['widths_desviations'] = remapped_widths_desviationss
    lslssls['openness'] = remapped_openness
    lslssls['closeness400'] = remapped_closeness400
    lslssls['closeness_global'] = remapped_closeness_global
    lslssls['betweenness_metric_n'] = remapped_betweenness_metric_n
    lslssls['betweenness_metric_e'] = remapped_betweenness_metric_e
    lslssls['straightness'] = remapped_straightness
    lslssls['speed'] = remapped_speed
    lslssls['travel'] = remapped_travel
    lslssls['food'] = remapped_food
    lslssls['education'] = remapped_education
    lslssls['transport'] = remapped_transport
    lslssls['shop'] = remapped_shop
    lslssls['vegetation'] = remapped_vegetation
    lslssls['value_temperature'] = remapped_value_temperature
    lslssls['value_windSpeed'] = remapped_value_windSpeed
    lslssls['value_windDirection'] = remapped_value_windDirection
    lslssls['value_humidity'] = remapped_value_humidity
    lslssls['value_skyCover'] = remapped_value_skyCover
    lslssls['value_earthTemperature'] = remapped_value_earthTemperature
    lslssls['value_precipitationWater'] = remapped_value_precipitationWater
    lslssls['value_directIlluminance'] = remapped_value_directIlluminance
    lslssls['value_diffuseIlluminance'] = remapped_value_diffuseIlluminance
    lslssls['value_irradiation'] = remapped_value_irradiation
    lslssls['traffic'] = remapped_traffic
    lslssls['noise'] = remapped_noise

    cell_values = wlf2cero.nearest_neighbor(gdf_dataframe_for_grid_points, lslssls, return_dist=True)

    mass_addition=[]
    for i in range(len(cell_values)):
        jajajaj= (
            cell_values['width'][i]+
            cell_values['widths_desviations'][i]+
            cell_values['openness'][i]+
            cell_values['closeness400'][i]+
            cell_values['closeness_global'][i]+
            cell_values['betweenness_metric_n'][i]+
            cell_values['betweenness_metric_e'][i]+
            cell_values['straightness'][i]+
            cell_values['speed'][i]+
            cell_values['travel'][i]+
            cell_values['food'][i]+
            cell_values['education'][i]+
            cell_values['transport'][i]+
            cell_values['shop'][i]+
            cell_values['vegetation'][i]+
            cell_values['value_temperature'][i]+
            cell_values['value_windSpeed'][i]+
            cell_values['value_windDirection'][i]+
            cell_values['value_humidity'][i]+
            cell_values['value_skyCover'][i]+
            cell_values['value_earthTemperature'][i]+
            cell_values['value_precipitationWater'][i]+
            cell_values['value_directIlluminance'][i]+
            cell_values['value_diffuseIlluminance'][i]+
            cell_values['value_irradiation'][i]+
            cell_values['traffic'][i]+
            cell_values['noise'][i]            
            )/27
        mass_addition.append(jajajaj)
    cell_values['mass_addition']=mass_addition

    cell_values['cell_state'] = cell_values['mass_addition'].apply(lambda x: 0 if x<1 else 1)
    cell_values['relative_cell_height'] = 1

    # print(cell_values.crs)
    # print(len(cell_values))    
    
    ### user inputs

    # Both Directions = 0
    # Left Side       = 1
    # Right Side      = 2

    # Crossing               = 0
    # T-Junction Start Left  = 1
    # T-Junction Start Right = 2

    # populationThreshold = 0.85
    # junctionType = 1
    # branchingSteps = 2
    # growthAngle = 2
    # StreetBlockSize=100

    populationThreshold = pt
    junctionType = jt
    branchingSteps = bs
    growthAngle = ga
    StreetBlockSize=sbs

    ###
    segmentLength=StreetBlockSize/branchingSteps
    angleResolution = growthAngle/1
    waterAngleShift=0
    initialDirection=1
    heightGrid=cell_values['relative_cell_height'].tolist()
    populationGrid=cell_values['cell_state'].tolist()

    # pointGrid  = []
    # for i in range(len(xs)):
    #   p = rg.Point3d( xs[i], ys[i], 0 )
    #   pointGrid.append(p)

    boundingBox = rg.BoundingBox(min_x, min_y,0, max_x, max_y,0)
    def split(list_a, chunk_size):

        for i in range(0, len(list_a), chunk_size):
            yield list_a[i:i + chunk_size]

    chunk_size = int(len(populationGrid)/len(populationGrid))
    # my_list = [1,2,3,4,5,6,7,8,9]
    heatmap = list(split(heightGrid, chunk_size))
    population = list(split(populationGrid, chunk_size))

    # heatmap = list(heightGrid)
    # population = [populationGrid]

    config = configuration(segmentLength, growthAngle, angleResolution, waterAngleShift, branchingSteps, junctionType, populationThreshold, initialDirection, heatmap, population, boundingBox)
    
    class Bounds:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

    class Quadtree:
        
        def __init__(self, bounds,  isLeaf = True, objects = [], objectsO = [], max_objects = 10, max_levels = 4, level = 0):
            self.bounds = bounds
            self.max_objects = max_objects
            self.max_levels = max_levels
            self.level = level
            self.objects = objects
            self.objectsO = objectsO
            self.isLeaf = isLeaf
            self.topRight = None
            self.topLeft = None
            self.bottomRight = None
            self.bottomLeft = None

        # split this node, moving all objects to their corresponding subnode
        def split(self):
            
            self.isLeaf = False
            level = self.level + 1
            width = self.bounds.width / 2.0
            height = self.bounds.height / 2.0
            x = self.bounds.x
            y = self.bounds.y
            self.topRight = Quadtree(Bounds(x+width, y, width, height),True, [], [], self.max_objects, self.max_levels, level)
            self.topLeft = Quadtree(Bounds(x, y, width, height), True, [], [],self.max_objects, self.max_levels, level)
            self.bottomLeft = Quadtree(Bounds(x, y+height, width, height), True, [], [],self.max_objects, self.max_levels, level)
            self.bottomRight = Quadtree(Bounds(x+width, y+height, width, height), True, [], [],self.max_objects, self.max_levels, level)
            for i in range(0, len(self.objects)):
                rect = self.objects[i]
                obj = self.objectsO[i]
                relevant_nodes =self.getRelevantNodes(rect)
                if(relevant_nodes[0]):
                    self.topRight.insert(rect, obj)
                if(relevant_nodes[1]):
                    self.topLeft.insert(rect, obj)
                if(relevant_nodes[2]):
                    self.bottomLeft.insert(rect, obj)
                if(relevant_nodes[3]):
                    self.bottomRight.insert(rect, obj)
            self.objects[:] = []
            self.objectsO[:] = []
        
        def getRelevantNodes(self, r):
            midX = self.bounds.x + (self.bounds.width / 2.0)
            midY = self.bounds.y + (self.bounds.height /2.0)
            qs = [False,False,False,False]
            isTop = False
            if r.y <= midY:
                isTop = True
            isBottom = False
            if r.y + r.height > midY:
                isBottom = True
            if r.x <= midX:
                if isTop:
                    qs[1] = True
                if isBottom:
                    qs[2] = True
            if r.x + r.width > midX:
                if isTop:
                    qs[0] = True
                if isBottom:
                    qs[3] = True
            return qs

        #Insert object into the tree.
    #If the tree exceeds the capacity, it will be split.
        def insert(self, pRect, obj):
            if not self.isLeaf:
                relevant_nodes =self.getRelevantNodes(pRect)
                if(relevant_nodes[0]):
                    self.topRight.insert(pRect, obj)
                if(relevant_nodes[1]):
                    self.topLeft.insert(pRect, obj)
                if(relevant_nodes[2]):
                    self.bottomLeft.insert(pRect, obj)
                if(relevant_nodes[3]):
                    self.bottomRight.insert(pRect, obj)
                return
            self.objects.append(pRect)
            self.objectsO.append(obj)
            if len(self.objects) > self.max_objects and self.level < self.max_levels:
                self.split()

        #Return all objects that could collide with the given bounds
        def retrieve(self, pRect):
            if self.isLeaf:
                return self.objectsO
            relevant = []
            relevant_nodes =self.getRelevantNodes(pRect)
            if(relevant_nodes[0] and self.topRight != None):
                relevant = relevant + self.topRight.retrieve(pRect)
            if(relevant_nodes[1] and self.topLeft != None):
                relevant = relevant + self.topLeft.retrieve(pRect)
            if(relevant_nodes[2] and self.bottomLeft != None):
                relevant = relevant + self.bottomLeft.retrieve(pRect)
            if(relevant_nodes[3] and self.bottomRight != None):
                relevant = relevant + self.bottomRight.retrieve(pRect)
            
            return relevant        

        def retrieveBounds(self):
            if self.isLeaf:
                return [self.bounds]
            relevant = []
            relevant_nodes =self.getRelevantNodes(self.bounds)
            if(relevant_nodes[0]):
                relevant = relevant + self.topRight.retrieveBounds()
            if(relevant_nodes[1]):
                relevant = relevant + self.topLeft.retrieveBounds()
            if(relevant_nodes[2]):
                relevant = relevant + self.bottomLeft.retrieveBounds()
            if(relevant_nodes[3]):
                relevant = relevant + self.bottomRight.retrieveBounds()
            return relevant


    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    def subtractPoints(p1, p2):
        return Point(p1.x-p2.x, p1.y - p2.y)

    def crossProduct(a, b):
        return a.x * b.y - a.y * b.x

    def lineSegementsIntersect(p,p2,q, q2, omitEnds):
        r = subtractPoints(p2,p)
        s = subtractPoints(q2, q)
        uNumerator = crossProduct(subtractPoints(q, p), r)
        denominator = crossProduct(r, s)
        if 0.0==uNumerator and 0.0 == denominator:
            return False
        if 0.0 == denominator:
            return False
        u = uNumerator / denominator
        t = crossProduct(subtractPoints(q,p), s) / denominator
        intersect = False
        if omitEnds:
            intersect = 0.001 < t and (0.999 > t and (0.001 < u and 0.999 > u))
        else:
            intersect = 0.0 <= t and (1.0 >= t and (0.0 <= u and 1.0 >= u))
        if intersect:
            x = p.x + t * r.x
            y = p.y + t * r.y
            return {"point": Point(x, y),"t": t}
        else:
            return intersect

    def minDegreeDifference(val1, val2):
        bottom = abs(val1 - val2) % 180.0
        return min(bottom, abs(bottom-180.0))

    def equalV(a, b):
        e = subtractPoints(a, b)
        return 0.00001 > lengthV2(e)

    def dotProduct(a, b):
        return a.x + b.x + a.y * b.y

    def length(a, b):
        return lengthV(subtractPoints(b,a))

    def length2(a, b):
        return lengthV2(subtractPoints(b,a))

    def lengthV(a):
        return math.sqrt(lengthV2(a))

    def lengthV2(a):
        return a.x * a.x + a.y * a.y

    def angleBetween(a, b):
        if((lengthV(a) * lengthV(b)) > 0.0):
            angleRad = math.acos((a.x * b.x + a.y * b.y) / (lengthV(a) * lengthV(b)))
        else:
            angleRad = math.acos(0.0)
        return 180.0 * angleRad / math.pi

    def sign(a):
        if 0.0 <= a:
            return 1
        elif 0.0 > a:
            return -1.0
        #else:
            #return 0.0

    def fractionBetween(a, b, e):
        b = subtractPoints(b,a)
        x = a.x + b.x * e
        y = a.y + b.y * e
        return Point(x, y)

    def randomRange(a, b):
        return random.random() * (b - a) + a

    def addPoints(a, b):
        x = a.x + b.x
        y = a.y + b.y
        return Point(x, y)

    def distanceToLine(a, b, e):
        d = subtractPoints(a,b)
        e = subtractPoints(e, b)
        proj = project(d, e)
        c = proj["projected"]
        b = addPoints(b, c)
        distance2 = length2(b, a)
        pointOnLine = b
        lineProj2 = sign(proj["dotProduct"]) * lengthV2(c)
        l2 = lengthV2(e)
        return {"distance2": distance2, "pointOnLine": pointOnLine, "lineProj2": lineProj2, "length2": l2}

    def project(a, b):
        e = dotProduct(a, b)
        lv2 = lengthV2(b)
        projected = Point(0, 0)
        if(lv2 != 0):
            projected = multVScalar(b, e / lv2)
        return {"dotProduct": e, "projected": projected}

    def multVScalar(a, b):
        x = a.x * b
        y = a.y * b
        return Point(x, y)

    def divVScalar(a, b):
        x = a.x / b
        y = a.y / b
        return Point(x, y)

    def lerp(a, b, t):
        return a * (1.0 - t) + b * t

    def lerpV(a, b, t):
        x = lerp(a.x, b.x, t)
        y = lerp(a.y, b.y, t)
        return Point(x, y)

    def randomNearCubic(b):
        d = math.pow(abs(b), 3.0)
        c = 0.0
        while c == 0.0 or random.random() < math.pow(abs(c), 3.0) / d:
            c = random.uniform(-b, b)
        return c

    # """


    # Heatmap


    # """

    class Heatmap:
        def __init__(self, grid = [], minX=0.0, minY=0.0, maxX=1000.0, maxY = 1000.0):
            self.grid = grid
            self.gridXMax = len(grid)-1
            self.gridYMax = len(grid[0])-1
            self.minX = minX
            self.minY = minY
            self.maxX = maxX
            self.maxY = maxY
            self.boundsX = maxX-minX
            self.boundsY = maxY-minY
        
        def valueSegment(self, s):
            value = (self.valueAt(s.start.x, s.start.y) + self.valueAt(s.end.x, s.end.y)) / 2.0
            return value

        def valueAtClosest(self, x, y):
            # find closest neighbouring cells
            cellX = round(((x-self.minX)/self.boundsX)*self.gridXMax)
            if cellX > self.gridXMax:
                cellX = self.gridXMax
            elif cellX < 0:
                cellX = 0
            cellY = round(((y-self.minY)/self.boundsY)*self.gridYMax)
            if cellY > self.gridYMax:
                cellY = self.gridYMax
            elif cellY < 0:
                cellY = 0
            return self.grid[int(round(cellX))][int(round(cellY))]

        def valueAt(self, x, y):
            # find closest neighbouring cells
            cellX = ((x-self.minX)/self.boundsX)*self.gridXMax
            cellXLow = int(math.floor(cellX))
            cellXHigh = int(math.ceil(cellX))
            if(cellXLow < 0):
                cellXLow = 0
                cellXHigh = 1
            if(cellXHigh >= self.gridXMax):
                cellXHigh = self.gridXMax
                cellXLow = self.gridXMax-1

            cellY = ((y-self.minY)/self.boundsY)*self.gridYMax
            cellYLow = int(math.floor(cellY))
            cellYHigh = int(math.ceil(cellY))
            if(cellYLow < 0):
                cellYLow = 0
                cellYHigh = 1
            if(cellYHigh >= self.gridYMax):
                cellYHigh = self.gridYMax
                cellYLow = self.gridYMax-1

            # interpolation between closest neighbours
            weightCell0 = (1-((cellX - cellXLow) * (cellY - cellYLow)))
            # print(weightCell0)
            weightCell1 = (1-((cellXHigh - cellX) * (cellY - cellYLow)))
            weightCell2 = (1-((cellXHigh - cellX) * (cellYHigh - cellY)))
            weightCell3 = (1-((cellX - cellXLow) * (cellYHigh - cellY)))
            valCell0 = self.grid[cellXLow][cellYLow] * weightCell0
            valCell1 = self.grid[cellXHigh][cellYLow] * weightCell1
            valCell2 = self.grid[cellXHigh][cellYHigh] * weightCell2
            valCell3 = self.grid[cellXLow][cellYHigh]  * weightCell3

            cellValueX = (valCell0 + valCell1 + valCell2 + valCell3) / (weightCell0 + weightCell1 + weightCell2 + weightCell3)
            return cellValueX

        def getFlattestDirection(self, segment, minAngle = -config.BRANCH_ANGLE, maxAngle = config.BRANCH_ANGLE, steps = 5, length = config.SEGMENT_LENGTH):
            steepness = 1
            bestAngle = 0.0
            startValue = self.valueAt(segment.end.x, segment.end.y)
            if(steps < 2):
                steps = 2
            for i in range(steps):
                curAngle = ((maxAngle-minAngle)/float(steps-1))*i + minAngle
                point = segment.pointInDirection(segment.end, segment.dir()+curAngle, length)
                
                curSteepness = abs(startValue-self.valueAt(point.x, point.y))
                if(curSteepness < steepness):
                    steepness = curSteepness
                    bestAngle = curAngle
            return bestAngle
        
        def getSteepestDirection(self, segment, minAngle = -config.BRANCH_ANGLE, maxAngle = config.BRANCH_ANGLE, steps = 5, length = config.SEGMENT_LENGTH):
            steepness = 0
            bestAngle = 0.0
            startValue = self.valueAt(segment.end.x, segment.end.y)
            if(steps < 2):
                steps = 2
            for i in range(steps):
                curAngle = ((maxAngle-minAngle)/float(steps-1))*i + minAngle
                point = segment.pointInDirection(segment.end, segment.dir()+curAngle, length)

                curValue = self.valueAt(point.x, point.y)
                curSteepness = abs(startValue-curValue)
                if(curSteepness > steepness):
                    steepness = curSteepness
                    bestAngle = curAngle
            return bestAngle
        
        def getCloseToWaterDirection(self, segment, minAngle = -config.BRANCH_ANGLE, maxAngle = config.BRANCH_ANGLE, steps = config.BRANCH_ANGLE_STEPS, length = config.SEGMENT_LENGTH):
            minWaterAngle = float("inf")

            optimalWaterAngle = self.getWaterflowDirection(segment, 16, length) - config.WATER_ANGLE_SHIFT

            if(segment.q.perpendicular):
                optimalWaterAngle = optimalWaterAngle+90.0
            optimalWaterAngle = optimalWaterAngle % 180
            if(abs(optimalWaterAngle-180.0) < optimalWaterAngle):
                optimalWaterAngle -= 180.0
            bestAngle = 0.0
            startValue = self.valueAt(segment.end.x, segment.end.y)
            if(steps < 2):
                steps = 2
            if(maxAngle < optimalWaterAngle):
                bestAngle = maxAngle
            elif(minAngle > optimalWaterAngle):
                bestAngle = minAngle
            else:
                bestAngle = optimalWaterAngle
            return bestAngle

        def getWaterflowDirection(self, segment, steps = 16, length = config.SEGMENT_LENGTH):
            return self.getSteepestDirection(segment, -180+360/steps, 180, steps-1, length)
            
            

    # """


    # Segment Metainfo


    # """


    class Metainfo:
        def __init__(self, severed = None, perpendicular = False, step = 0):
            self.severed = severed
            self.perpendicular = perpendicular
            self.step = step

    # """


    # Segment 


    # """
    class Segment:
        links = {"b": [], "f" : []}
        
        def __init__(self, startPoint, endPoint, t, q = Metainfo()):
            self.start = copy.deepcopy(startPoint)
            self.end = copy.deepcopy(endPoint)
            self.q = copy.deepcopy(q)
            if self.q == None:
                self.q = Metainfo()
            self.t = t
            self.previousSegment = None

        def setupBranchLinks(self):
            if self.previousSegment != None and isinstance(self.previousSegment, Segment):
                previousSegment = self.previousSegment
                for link in previousSegment.links["f"]:
                    self.links["b"].append(link)
                    if previousSegment in link.links["b"]:
                        link.links["b"].append(self)
                    elif previousSegment in link.links["f"]:
                        link.links["f"].append(self)
                previousSegment.links["f"].append(self)
                self.links["b"].append(previousSegment)
                return True #self.links["b"]
            else:
                return False


        def dir(self):
            vector = subtractPoints(self.end, self.start)
            return -1.0 * sign(crossProduct(Point(0.0, 1.0), vector)) * angleBetween(Point(0.0,1.0), vector)

        def length(self):
            return length(self.start, self.end)

        def length2(self):
            return length2(self.start, self.end)
        
        def limits(self):
            x = min(self.start.x, self.end.x)
            y = min(self.start.y, self.end.y)
            width = abs(self.start.x - self.end.x)
            height = abs(self.start.y - self.end.y)
            return Bounds(x,y,width,height)
        
        #def debugLinks()

        def startIsBackwards(self):
            if len(self.links["b"]) > 0:
                if equalV(self.links["b"][0].start, self.start) or equalV(self.links["b"][0].end, self.start):
                    return True
                else:
                    return False
            elif(len(self.links["f"]) > 0):
                if equalV(self.links["f"][0].start, self.end) or equalV(self.links["f"][0].end, self.end):
                    return True
                else:
                    return False
        
        def split(self, point, segment, segmentList, qTree):
            splitPart = self.clone(self.t, self.q)
            startIsBackwards = self.startIsBackwards()
            segmentList.append(splitPart)
            qTree.insert(splitPart.limits(), splitPart)
            splitPart.end = point
            self.start = point

            splitPart.links["b"] = self.links["b"][:1]
            splitPart.links["f"] = self.links["f"][:1]

            if startIsBackwards:
                firstSplit = splitPart
                secondSplit = self
                fixLinks = splitPart.links["b"]
            else:
                firstSplit = self
                secondSplit = splitPart
                fixLinks = splitPart.links["f"]
            for link in fixLinks:
                if self in link.links["b"]:
                    index = link.links["b"].index(self)
                    link.links["b"][index] = splitPart
                elif self in link.links["f"]:
                    index = link.links["f"].index(self)
                    link.links["f"][index] = splitPart
            firstSplit.links["f"] = [segment, secondSplit]
            secondSplit.links["b"] = [segment, firstSplit]
            segment.links["f"].append(firstSplit)
            segment.links["f"].append(secondSplit)


        def clone(self, t = None, q = None):
            if t == None:
                t = (self.t)
            if q == None:
                q = (self.q)
            return Segment((self.start), (self.end), t, q)
        
        @staticmethod
        def pointInDirection(start, dir = 90.0, length = config.SEGMENT_LENGTH):
            x = start.x + length * math.sin(dir * math.pi / 180.0)
            y = start.y + length * math.cos(dir * math.pi / 180.0)
            return Point(x, y)

        @staticmethod
        def usingDirection(startPoint, t, q, dir = 90.0, length = config.SEGMENT_LENGTH):
            x = startPoint.x + length * math.sin(dir * math.pi / 180.0)
            y = startPoint.y + length * math.cos(dir * math.pi / 180.0)
            endPoint = Point(x, y)
            return Segment(startPoint, endPoint, t, q)
        
        def intersectWith(self, s):
            return lineSegementsIntersect(self.start, self.end, s.start, s.end, True)


    # """


    # Local Growth Constraints


    # """

    def localConstraints(segment, segments, qTree):
        action = {"priority": 0, "objects" : [None, None], "func" : {"intersection": False, "snapping": False, "radius": False}, "t" : None}       
        others = qTree.retrieve(segment.limits())
        for other in others:
            # print(action["priority"])
            #intersection check
            if action["priority"] <= 4:
                intersection = segment.intersectWith(other)
                if intersection:
                    if intersection["t"] > 0.01:
                        if action["t"] == None or intersection["t"] < action["t"]:
                            action["t"] = intersection["t"]
                            action["priority"] = 4
                            action["func"]["intersection"] = True
                            action["objects"] = [other, intersection["point"]] 
            #snap to crossing with radius check
            if action["priority"] <= 3:
                #current segment's start must have been checked to have been created.
                #other segment's start must have a corresponding end.
                if not equalV(segment.start, other.end) > 0.01:
                    if length(segment.end, other.end) <= config.ROAD_SNAP_DISTANCE:
                        point = other.end
                        action["priority"] = 3
                        action["func"]["snapping"] = True
                        action["objects"] = [other, point]
            #intersection within radius check
            if action["priority"] <= 2:
                #make sure segment does not start on same line
                #might lead to BUG?
                if not equalV(segment.start, other.start) and not equalV(segment.start, other.end):
                    distToLine = distanceToLine(segment.end, other.start, other.end)
                    distance2 = distToLine["distance2"]
                    pointOnLine = distToLine["pointOnLine"]
                    lineProj2 = distToLine["lineProj2"]
                    length2 = distToLine["length2"]
                    if distance2 > 0.01 and not equalV(segment.start, pointOnLine):
                        if distance2 < config.ROAD_SNAP_DISTANCE * config.ROAD_SNAP_DISTANCE and lineProj2 >= 0.0 and lineProj2 <= length2:
                            point = pointOnLine
                            action["priority"] = 2
                            action["func"]["radius"] = True
                            action["objects"] = [other, point]
        if action["objects"][0] != None:
            if action["func"]["radius"] == True:
                other = action["objects"][0]
                point = action["objects"][1]
                segment.end = point
                segment.q.severed = True
                if minDegreeDifference(other.dir(), segment.dir()) < config.MINIMUM_INTERSECTION_DEVIATION:
                    return False
                other.split(point, segment, segments, qTree)
                return True
            elif action["func"]["snapping"] == True:
                other = action["objects"][0]
                point = action["objects"][1]
                segment.end = point
                segment.q.severed = True
                links = []
                #check for duplicate lines, don't add if it exists
                if(equalV(other.start, segment.end) and equalV(other.end, segment.start) or equalV(other.start, segment.start) and equalV(other.end, segment.end)):
                    return False
                #update links of otherSegment corresponding to other.r.end
                if other.startIsBackwards():
                    links = other.links["f"]
                else:
                    links = other.links["b"]
                #check for duplicate lines in links, don't add if it exists
                #this should be done before links are setup, to avoid having to undo that step
                # for link in links:
                #     if(equalV(link.start, segment.end) and equalV(link.end, segment.start) or equalV(link.start, segment.start) and equalV(link.end, segment.end)):
                #         return False
                # for link in links:
                #     if other in link.links["b"]:
                #         if(link.links["b"] != links):
                #             link.links["b"].append(segment)
                    # elif other in link.links["f"]:          
                    #     if(link.links["f"] != links):
                    #           link.links["f"].append(segment)
                    # segment.links["f"].append(link)
                links.append(segment)
                segment.links["f"].append(other)
                    
                return True
            elif action["func"]["intersection"] == True:
                other = action["objects"][0]
                intersection = action["objects"][1]
                if minDegreeDifference(other.dir(), segment.dir()) < config.MINIMUM_INTERSECTION_DEVIATION:
                    return False
                other.split(intersection, segment, segments, qTree)
                segment.end = intersection
                segment.q.severed = True
                return True
            else:
                return True
        else:
            return True


    # """


    # Branching Constraints


    # """

    def branchConstraints(segment, qTree):
        #close similar branch
        others = qTree.retrieve(segment.limits())
        for other in others:
            #if  not same start
            if not equalV(segment.start, other.start):
                #if segment close enough
                if length2(segment.end, other.end) <= config.ROAD_SIMILARITY_DISTANCE * config.ROAD_SIMILARITY_DISTANCE or length2(segment.end, other.start) <= config.ROAD_SIMILARITY_DISTANCE*config.ROAD_SIMILARITY_DISTANCE:
                    #if direction is similar
                    if minDegreeDifference(other.dir(), segment.dir()) < config.ROAD_SIMILARITY_MINIMUM_DEVIATION_ANGLE:
                        return True
        return False

    # """


    # Global Goals


    # """

    def globalGoalsGenerate(previousSegment, heatmap, qTree):
        newBranches = []

        if previousSegment.q != None and not previousSegment.q.severed:
            def template(direction, length, t, q):
                return Segment.usingDirection(previousSegment.end, t, q, previousSegment.dir() + direction, length)
            def templateContinue(direction):
                q = Metainfo(previousSegment.q.severed, previousSegment.q.perpendicular, previousSegment.q.step+1)
                return template(direction, previousSegment.length(), 0.0, q)
            def templateBranch(direction):
                q = Metainfo(None, not previousSegment.q.perpendicular, 0)
                return template(direction, config.SEGMENT_LENGTH, 0.0, q)
            #get best water direction straight
            bestDir = heatmap.getCloseToWaterDirection(previousSegment, -config.BRANCH_ANGLE, config.BRANCH_ANGLE, config.BRANCH_ANGLE_STEPS, previousSegment.length())
            continueStraight = templateContinue(bestDir)
            newBranches.append(continueStraight)
            if previousSegment.q.step >= config.BRANCH_STEP:
                #get best water direction right
                if (previousSegment.q.step - config.BRANCH_STEP_RIGHT) % config.BRANCH_STEP == 0:
                    bestDir = heatmap.getCloseToWaterDirection(previousSegment, +90.0 - config.BRANCH_ANGLE, 90.0 + config.BRANCH_ANGLE, config.BRANCH_ANGLE_STEPS, previousSegment.length())       
                    newSegment = templateBranch(bestDir)
                    newBranches.append(newSegment)
                #get best water direction left
                if (previousSegment.q.step - config.BRANCH_STEP_LEFT) % config.BRANCH_STEP == 0:
                    bestDir = heatmap.getCloseToWaterDirection(previousSegment, -90.0 -config.BRANCH_ANGLE, -90.0 + config.BRANCH_ANGLE, config.BRANCH_ANGLE_STEPS, previousSegment.length())
                    newSegment = templateBranch(bestDir) 
                    newBranches.append(newSegment)

        for branch in newBranches:
            #setup links between each current branch and each existing branch stemming from the previous segment
            branch.previousSegment = previousSegment
        return newBranches

    # """


    # Priority Queue


    # """
    class PriorityQueue:
        ####
        # 
        # 
        # 
        # def __init__()
        # *ele allows providing multiple arguments
        def __init__(self):
            self.elements = []

        def getPriority(self, ele):
            return ele.t

        def enqueue(self, ele): #*
            if isinstance(ele, Segment):
                ele = [ele]
            for el in ele:
                self.elements.append(el)

        def dequeue(self):
            minT = float("inf")
            minT_i = 0
            for i in range(len(self.elements)):
                t = self.getPriority(self.elements[i])
                if t < minT:
                    minT = t
                    minT_i = i
            el = self.elements[minT_i:minT_i+1][0]
            self.elements = self.elements [:minT_i] + self.elements [minT_i+1:]
            
            return el
        
        def empty(self):
            return len(self.elements) == 0



    def makeInitialSegments(rootSegment, heatmap):
        if config.INITIAL_DIRECTION == 1:
            return [rootSegment]

        oppositeDirection = rootSegment.clone(0.0, Metainfo(False, rootSegment.q.perpendicular, 0))
        newEnd = Point(rootSegment.start.x - (rootSegment.end.x-rootSegment.start.x), rootSegment.start.y - (rootSegment.end.y-rootSegment.start.y))
        oppositeDirection.end = newEnd
        if config.INITIAL_DIRECTION == 2:
            return [oppositeDirection]
        
        oppositeDirection.links["b"].append(rootSegment)
        rootSegment.links["b"].append(oppositeDirection)
        return [rootSegment, oppositeDirection]


    def makeExistingSegments(x,y,heatmap, population, segments = [], qTree = None):
        length = config.SEGMENT_LENGTH
        initialSegments = []
        if(len(segments)<=0):
            initialSegment = Segment(Point(x-length, y), Point(x,y), 0.0, Metainfo(False, False, 0))
            direction = heatmap.getWaterflowDirection(initialSegment,32, length)
            initialSegments.append(Segment.usingDirection(initialSegment.start, 0.0, Metainfo(False, initialSegment.q.perpendicular, 0), initialSegment.dir() + direction, -length))
        else:
            center = Point(x,y)
            sortedSegments = []
            toLeft = False
            toRight = False
            if config.INITIAL_DIRECTION == 0 or config.INITIAL_DIRECTION == 1:
                toLeft = True
            if config.INITIAL_DIRECTION == 0 or config.INITIAL_DIRECTION == 2:
                toRight = True
            for i in range(len(segments)):
                curDirection = heatmap.getWaterflowDirection(segments[i], 32, length)
                if(curDirection > 45.0):
                    segments[i].q.perpendicular = True
                qTree.insert(segments[i].limits(), segments[i])
                #create branches
                initialSegment = Segment.usingDirection(segments[i].start, 0.0, Metainfo(False, not segments[i].q.perpendicular, 0), segments[i].dir()-90, length)

                direction = heatmap.getCloseToWaterDirection(initialSegment, -config.BRANCH_ANGLE, config.BRANCH_ANGLE, 16, length)
                
                if (i - config.BRANCH_STEP_RIGHT) % (config.BRANCH_STEP) == 0 and toRight == True:
                    initialSegments.append(Segment.usingDirection(initialSegment.start, 0.0, Metainfo(False, initialSegment.q.perpendicular, 0), initialSegment.dir() + direction, -length))
                if (i - config.BRANCH_STEP_LEFT) % (config.BRANCH_STEP) == 0 and toLeft == True:
                    initialSegments.append(Segment.usingDirection(initialSegment.start, 0.0, Metainfo(False, initialSegment.q.perpendicular, 0), initialSegment.dir() + direction, length))
        filteredSegments = []
        for segment in initialSegments:
            if(populationMap.valueAtClosest(segment.end.x, segment.end.y) <= config.POPULATION_THRESHOLD):
                filteredSegments.append(segment)
        return filteredSegments

    def generationStep(priorityQ, segments, qTree, heatmap, populationMap):
        newSegments = []
        if( not priorityQ.empty()):
    
            minSegment = priorityQ.dequeue()
            accepted = localConstraints(minSegment, segments, qTree)
            # print(accepted)
            # print(accepted)
            if(populationMap.valueAtClosest(minSegment.end.x, minSegment.end.y) > config.POPULATION_THRESHOLD):
                accepted = False
            if accepted and minSegment.q.step == 0:
                accepted = not branchConstraints(minSegment, qTree)
            if accepted:
                
                if minSegment.previousSegment != None and isinstance(minSegment.previousSegment, Segment) and len(minSegment.links["b"]) == 0:
                    minSegment.setupBranchLinks()

                segments.append(minSegment)
                newSegments.append(minSegment)
                qTree.insert(minSegment.limits(), minSegment)
                for newSegment in globalGoalsGenerate(minSegment, heatmap, qTree):
                    newSegment.t = minSegment.t + 1.0 + newSegment.t
                    priorityQ.enqueue(newSegment)

        return newSegments

    """


    Generator Results


    # """
    class GeneratorResult:
        def __init__(self, segments, priorityQ, qTree, terrainHeightMap, populationMap):
            self.segments = segments
            self.priorityQ = priorityQ
            self.qTree = qTree
            self.terrainHeightMap = terrainHeightMap
            self.populationMap = populationMap
    
    dataframe_for_center_point = pd.DataFrame()
    gdf_dataframe_for_center_point= gpd.GeoDataFrame(dataframe_for_center_point, geometry=[list_pois[0]])
    gdf_dataframe_for_center_point.set_crs(4326, inplace=True)
    gdf_dataframe_for_center_point = gdf_dataframe_for_center_point.to_crs(3857)
    startPoint = rg.Point3d( gdf_dataframe_for_center_point.centroid.x[0], gdf_dataframe_for_center_point.centroid.y[0], 0 )

    dataframe_for_first_grow = pd.DataFrame()
    gdf_dataframe_for_first_growt= gpd.GeoDataFrame(dataframe_for_first_grow, geometry=exploded_int_lines)
    gdf_dataframe_for_first_growt.set_crs(4326, inplace=True)
    gdf_dataframe_for_first_growt = gdf_dataframe_for_first_growt.to_crs(3857)
    
    # numberiterations = 2000
    numberiterations = iter

    dataframe_for_center_point = pd.DataFrame()
    gdf_dataframe_for_center_point= gpd.GeoDataFrame(dataframe_for_center_point, geometry=[list_pois[0]])
    gdf_dataframe_for_center_point.set_crs(4326, inplace=True)
    gdf_dataframe_for_center_point = gdf_dataframe_for_center_point.to_crs(3857)

    startPoint = rg.Point3d( gdf_dataframe_for_center_point.centroid.x[0], gdf_dataframe_for_center_point.centroid.y[0], 0 )
    multi_line_pepe = gdf_dataframe_for_first_growt.geometry.values
    existingStreets = []
    for i in multi_line_pepe:
        x,y = i.coords.xy
        x  = x.tolist()
        y  = y.tolist()
        pts = []
        for a,b in zip(x,y):
            p = rg.Point3d( float(a), float(b), 0 )
            pts.append(p)
        poly = rg.Line(pts[0],pts[1])
        existingStreets.append(poly)
    config = config

    generatorResult = 2
    segments = []
    terrainHeightMap = Heatmap(config.HEATMAP, config.BOUNDS.Min.X, config.BOUNDS.Min.Y, config.BOUNDS.Max.X, config.BOUNDS.Max.Y)
    populationMap = Heatmap(config.POPULATION, config.BOUNDS.Min.X, config.BOUNDS.Min.Y, config.BOUNDS.Max.X, config.BOUNDS.Max.Y)
    QUADTREE_PARAMS = Bounds(-2000.0,-2000.0,4000.0,4000.0)
    QUADTREE_MAX_OBJECTS = 10
    QUADTREE_MAX_LEVELS = 10
    quadtree = Quadtree(QUADTREE_PARAMS, True,[], [], QUADTREE_MAX_OBJECTS, QUADTREE_MAX_LEVELS, 0)

    results = GeneratorResult([], PriorityQueue(), quadtree, terrainHeightMap, populationMap)

    for segment in existingStreets:
        segments.append(Segment(Point(segment.From.X, segment.From.Y), Point(segment.To.X, segment.To.Y), 0.0, Metainfo(False, False, 0)))
        
    initialSegments = makeExistingSegments(startPoint.X, startPoint.Y, results.terrainHeightMap , results.populationMap, segments, results.qTree)
    segments.extend(initialSegments)
    results.priorityQ.enqueue(initialSegments)
    for segment in segments:
        results.segments.append(segment)
    generatorResult = results


    cacas = []
    cacas.append(generatorResult)
    run=1
    while run <= numberiterations:
        print(run)

        segments = []
        results = cacas[run-1]

        startTime = time.time()
        segments.extend(generationStep(results.priorityQ, results.segments, results.qTree, results.terrainHeightMap, results.populationMap))

        # print(results.priorityQ.dequeue())
        lines = []
        colors = []
        generatorResult = results
        cacas.append(generatorResult)
        run += 1
            # except TimeoutException:
            #     continue # continue the for loop if function A takes more than 5 second
            # else:
            #     # Reset the alarm
            #     signal.alarm(0)

    generatorResult = generatorResult

    generatorResult = generatorResult
    segments_normales = []
    # segments_normales =[]
    segmentType = []
    segmentStep = []
    segmentSevered = []
    segmentPerpendicular = []
    segmentPriority = []
    for segment in generatorResult.segments:
        if(segment.length2() > 0.00001):
            # segments_d.append(rg.Line(rg.Point3d(segment.start.x, segment.start.y, 0.0), rg.Point3d(segment.end.x, segment.end.y, 0.0)))
            segments_normales.append(LineString([(segment.start.x,segment.start.y), (segment.end.x,segment.end.y)]))
            segmentStep.append(segment.q.step)
            segmentSevered.append(segment.q.severed)
            segmentPerpendicular.append(segment.q.perpendicular)
            segmentPriority.append(segment.t)

    len(segments_normales)

    list_pois[1]
    dataframe_seg_poly= pd.DataFrame()
    gdf_dataframe_seg_poly= gpd.GeoDataFrame(dataframe_seg_poly, geometry=[list_pois[1]])
    gdf_dataframe_seg_poly.set_crs(4326, inplace=True)
    gdf_dataframe_seg_poly = gdf_dataframe_seg_poly.to_crs(3857)

    true_false_final = []
    for i in segments_normales:
        true_false_final.append(i.intersects(gdf_dataframe_seg_poly.geometry[0]))

    segments_normales_final = []
    for i in range(len(true_false_final)):
        if true_false_final[i]== True:
            segments_normales_final.append(segments_normales[i])
    dataframe_segments_normals= pd.DataFrame()
    gdf_dataframe_segments_normals= gpd.GeoDataFrame(dataframe_segments_normals, geometry=segments_normales_final)
    gdf_dataframe_segments_normals.set_crs(3857, inplace=True)
    gdf_dataframe_segments_normals = gdf_dataframe_segments_normals.to_crs(4326)
    gdf_dataframe_segments_normals = gdf_dataframe_segments_normals.iloc[len(gdf_dataframe_for_first_growt): , :]
    final_segments = pd.concat([df_new_dataframe_outout,df_new_streets_intersect])
    final_segments = pd.concat([final_segments,gdf_dataframe_segments_normals])

    final_segments = final_segments.reset_index()
    # final_segments.plot()
    bwbw2=[]
    for i in range(len(df_new_dataframe_outout)+len(df_new_streets_intersect)):
        z = 'black'
        bwbw2.append(z)



    for i in range (len(gdf_dataframe_for_first_growt)):
        segmentSevered.remove(segmentSevered[0])

    for i in range(len(gdf_dataframe_segments_normals)):
        if segmentSevered[i] == False or None:
            z = 'red'
            bwbw2.append(z)
        else:
            z = 'green'
            bwbw2.append(z)
    
    multi_linefinal = final_segments.geometry.values
    a = []

    for w in range(len(final_segments)):
        # print(w)
        if w <= len(df_new_dataframe_outout)+len(df_new_streets_intersect):
            x,y = multi_linefinal[w].coords.xy
            x  = x.tolist()
            y  = y.tolist()

            coordinates = zip(x,y)
            b = list(coordinates)
            # co = []
            c = {
                "coordinates": b,
                "dates": ["2017-06-02T00:00:00", "2017-06-02T00:00:00"],
                "color": bwbw2[w],
                # "popup": "address1",
                # "weight": k[ia],
            }
            a.append(c)
        else:    
            dt = datetime(2017, 6, 2, 0, 0, 0)
            result = dt + timedelta(seconds=w-len(df_new_dataframe_outout))
            result = str(result).replace(" ", "T")
            x,y = multi_linefinal[w].coords.xy
            x  = x.tolist()
            y  = y.tolist()

            coordinates = zip(x,y)
            b = list(coordinates)
            # co = []
            c = {
                "coordinates": b,
                "dates": [result, result],
                "color": bwbw2[w],
                # "popup": "address1",
                # "weight": k[ia],
            }
            a.append(c)

    return point_central, a
