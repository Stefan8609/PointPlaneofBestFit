"""
[add description]

Written by Stefan Kildal-Brandt
"""

import numpy as np
from RigidBodyMovementProblem import findRotationAndDisplacement
import scipy.io as sio
from pymap3d import geodetic2ecef, ecef2geodetic
from geopy import distance

esv_table = sio.loadmat('../GPSData/global_table_esv.mat')
dz_array = esv_table['distance'].flatten()
angle_array = esv_table['angle'].flatten()
esv_matrix = esv_table['matrice']

def findTransponder(GPS_Coordinates, gps1_to_others, gps1_to_transponder):
    # Given initial information relative GPS locations and transponder and GPS Coords at each timestep
    xs, ys, zs = gps1_to_others.T
    initial_transponder = gps1_to_transponder
    n = len(GPS_Coordinates)
    transponder_coordinates = np.zeros((n, 3))
    for i in range(n):
        new_xs, new_ys, new_zs = GPS_Coordinates[i].T
        R_mtrx, d = findRotationAndDisplacement(np.array([xs,ys,zs]), np.array([new_xs, new_ys, new_zs]))
        transponder_coordinates[i] = np.matmul(R_mtrx, initial_transponder) + d
    return transponder_coordinates

def calculateTimes(guess, transponder_coordinates, sound_speed):
    times = np.zeros(len(transponder_coordinates))
    for i in range(len(transponder_coordinates)):
        distance = np.linalg.norm(transponder_coordinates[i] - guess)
        times[i] = distance / sound_speed
    return times

def haversine_distance(lat1, lon1, lat2, lon2): #Modified from Thalia
    lat1, lon1, lat2, lon2 = lat1*np.pi/180, lon1*np.pi/180, lat2*np.pi/180, lon2*np.pi/180
    #Radius of Earth
    R = 6371e3
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    #Haversine formula for horizontal distance
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c
#Make sure that this is actually right - Might be more accurate ways to do this

def find_esv(beta, dz):
    idx_closest_dz = np.searchsorted(dz_array, dz, side="left")
    idx_closest_dz = np.clip(idx_closest_dz, 0, len(dz_array)-1)
    idx_closest_beta = np.searchsorted(angle_array, beta, side="left")
    idx_closest_beta = np.clip(idx_closest_beta, 0, len(angle_array)-1)
    closest_esv = esv_matrix[idx_closest_dz, idx_closest_beta]
    return closest_esv

def calculateTimesRayTracing(guess, transponder_coordinates):
    hori_dist = np.sqrt((transponder_coordinates[:, 0] - guess[0])**2 + (transponder_coordinates[:, 1] - guess[1])**2)
    abs_dist = np.linalg.norm(transponder_coordinates - guess, axis=1)
    beta = np.arccos(hori_dist / abs_dist) * 180 / np.pi
    dz = np.abs(guess[2] - transponder_coordinates[:, 2])
    esv = find_esv(beta, dz)
    times = abs_dist / esv
    return times, esv

def computeJacobianRayTracing(guess, transponder_coordinates, times, sound_speed):
    # Computes the Jacobian, parameters are xyz coordinates and functions are the travel times
    diffs = transponder_coordinates - guess
    jacobian = -diffs / (times[:, np.newaxis] * (sound_speed[:, np.newaxis] ** 2))
    return jacobian

#Goal is to minimize sum of the difference of times squared
def geigersMethod(guess, times_known, transponder_coordinates_Found):
    #Use Geiger's method to find the guess of CDOG location which minimizes sum of travel times squared
    #Define threshold
    epsilon = 10**-5
    #Sound Speed of water (right now constant, later will use ray tracing)

    k=0
    delta = 1
    #Loop until change in guess is less than the threshold
    while np.linalg.norm(delta) > epsilon and k<100:
        times_guess, esv = calculateTimesRayTracing(guess, transponder_coordinates_Found)
        # times_guess = calculateTimesRayTracing(guess, transponder_coordinates_Found)
        jacobian = computeJacobianRayTracing(guess, transponder_coordinates_Found, times_guess, esv)
        delta = -1 * np.linalg.inv(jacobian.T @ jacobian) @ jacobian.T @ (times_guess-times_known)
        guess = guess + delta
        k+=1
    return guess

#XYZ in ECEF does not coordinate with z being depth and xy corresponding to horizontal!
#Need to account for this when getting the dz and horizontal distance.

#What is the best way to calculate horizontal distance?
#There is a considerable (8m) curvature of the earth of 10 km
#Could I project out the depth to be the same? Then get horizontal dist?

#Important to consider curvature effects. Make sure ray-tracing is correct
#Implement Bud's algorithm for ray-tracing Gauss-Newton

#Vectorize everything -- Should make code a decent amount faster (too slow as is)