import shapely.geometry
from sklearn.neighbors import BallTree
import math
import geopandas as gpd
import numpy as np
from shapely.geometry import Point as pit


def get_nearest(src_points, candidates, k_neighbors=1):
        """Find nearest neighbors for all source points from a set of candidate points"""

        # Create tree from the candidate points
        tree = BallTree(candidates, leaf_size=15, metric='haversine')

        # Find closest points and distances
        distances, indices = tree.query(src_points, k=k_neighbors)

        # Transpose to get distances and indices into arrays
        distances = distances.transpose()
        indices = indices.transpose()

        # Get closest indices and distances (i.e. array at index 0)
        # note: for the second closest points, you would take index 1, etc.
        closest = indices[0]
        closest_dist = distances[0]

        # Return indices and distances
        return (closest, closest_dist)
    
def nearest_neighbor(left_gdf, right_gdf, return_dist=False):


        left_geom_col = left_gdf.geometry.name
        right_geom_col = right_gdf.geometry.name

        # Ensure that index in right gdf is formed of sequential numbers
        right = right_gdf.copy().reset_index(drop=True)

        # Parse coordinates from points and insert them into a numpy array as RADIANS
        left_radians = np.array(left_gdf[left_geom_col].apply(lambda geom: (geom.x * np.pi / 180, geom.y * np.pi / 180)).to_list())
        right_radians = np.array(right[right_geom_col].apply(lambda geom: (geom.x * np.pi / 180, geom.y * np.pi / 180)).to_list())

        # Find the nearest points
        # -----------------------
        # closest ==> index in right_gdf that corresponds to the closest point
        # dist ==> distance between the nearest neighbors (in meters)

        closest, dist = get_nearest(src_points=left_radians, candidates=right_radians)

        # Return points from right GeoDataFrame that are closest to points in left GeoDataFrame
        closest_points = right.loc[closest]

        # Ensure that the index corresponds the one in left_gdf
        closest_points = closest_points.reset_index(drop=True)

        # Add distance if requested
        if return_dist:
            # Convert to meters from radians
            earth_radius = 6371000  # meters
            closest_points['distance'] = dist * earth_radius

        return closest_points

def remap(l):
        remaped = []
        for v in l:
            if max(l)-min(l) > 0:
                rst = ((v-min(l))/(max(l)-min(l)))*(1-0)+0
                remaped.append(rst)
            else:
                rst = (0+1)/2
                remaped.append(rst)
        return remaped

def order_points(picopiedra,ind):
        points_new = [ picopiedra.pop(ind) ]  # initialize a new list of points with the known first point
        pcurr      = points_new[-1]
        while len(picopiedra)>0:
            d      = np.linalg.norm(np.array(picopiedra) - np.array(pcurr), axis=1)  # distances between pcurr and all other remaining points
            ind    = d.argmin()                   # index of the closest point
            points_new.append( picopiedra.pop(ind) )  # append the closest point to points_new
            pcurr  = points_new[-1] 
            if len(picopiedra)==1:
            # points_new.append(points2[-1])
                break              # update the current point
        return points_new

def Random_Points_in_Polygon(polygon, number):
        kok = []
        minx, miny, maxx, maxy = polygon.bounds
        while len(kok) < number:
            pnt = pit(np.random.uniform(minx, maxx), np.random.uniform(miny, maxy))
            if polygon.contains(pnt):
                kok.append(pnt)
        return kok